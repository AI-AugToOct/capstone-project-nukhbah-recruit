"""
Resume LLM Pipeline (AR/EN) — Safe PII scrub + NER → LLM semantic filtering
----------------------------------------------------------------------------
Exports (import-only, no __main__):

parse_resume_with_llm(
    raw_text: str,
    job_desc: str,
    llm_backend: "LocalHFBackend|OpenAIBackend",
    llm_model: str = None,
    write_outputs: dict | None = None,
) -> dict

Returns:
{
  "candidate_id": str,
  "name": str | None,
  "email": str | None,
  "comparison_text": str  # PII-scrubbed & JD-relevant; ready for embeddings (done elsewhere)
}

Design:
1) Deterministic safety pass: NER (XLM-R) + regex to:
   - remove PII (PERSON/ORG/email/phone/URLs/IDs) and company names,
   - strip dates/tenures from experience (minimize embedding bias).
2) LLM pass (English prompts; AR/EN content accepted):
   - Select only lines relevant to the provided Job Description (JD).
   - Output strict JSON for kept lines per section.
3) Assemble final comparison_text from kept lines only; run a final scrub.

Notes:
- Arabic + English supported.
- No embeddings here; this file only cleans and prepares text.
"""

from __future__ import annotations
import re
import json
import uuid
import hashlib
import unicodedata
from typing import Dict, Any, Optional, List, Tuple

# =================== Normalization & Regex =================== #

def _normalize_text(t: str) -> str:
    t = unicodedata.normalize("NFKC", t or "")
    t = re.sub(r"-\n", "", t)             # OCR hyphen line-breaks
    t = re.sub(r"[\t\r]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r" {2,}", " ", t)
    return t.strip()

EMAIL_RE   = re.compile(r"\b[\w\.-]+@[\w\.-]+\.[A-Za-z]{2,}\b")
PHONE_RE   = re.compile(r"\b(?:\+?\d[\d\s\-()]{6,})\b")
URL_RE     = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
ID_HINT_RE = re.compile(r"\b(National ID|هوية|ID)[:\s]*([A-Z0-9\-]+)\b", re.IGNORECASE)

# split headers (both AR/EN)
SEC_HEADERS = {
    "skills": [r"\bskills?\b", r"\btechnical skills?\b", r"\bالمهارات\b"],
    "experience": [r"\bexperience\b", r"\bwork\b", r"\bemployment\b", r"\bالخبرات?\b", r"\bالخبرة\b"],
    "education": [r"\beducation\b", r"\bacademic\b", r"\bالتعليم\b", r"\bالدراسة\b"],
    "certifications": [r"\bcertifications?\b", r"\blicenses?\b", r"\bالشهادات\b"],
    "courses": [r"\bcourses?\b", r"\bالدورات\b", r"\bالدورات التدريبية\b"],
    "projects": [r"\bprojects?\b", r"\bالمشاريع\b"],
}

# date patterns to prune from experience (reduce bias in embeddings)
_MONTHS_RE = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|"
    r"يناير|فبراير|مارس|أبريل|ابريل|مايو|يونيو|يوليو|أغسطس|اغسطس|سبتمبر|أكتوبر|اكتوبر|نوفمبر|ديسمبر)\b",
    re.IGNORECASE
)
_DURATION_RE = re.compile(r"\b(\d+\s*(?:months?|years?|سن(?:ة|وات)))\b", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")

def _strip_list_marker(line: str) -> str:
    # remove leading bullets/dashes: -, •, *, –, —
    return re.sub(r"^\s*[-•*–—]+\s*", "", line)

def _drop_empty_labels(text: str) -> str:
    # e.g., "Phone: +", "Email:", "LinkedIn:" with no value
    t = re.sub(r"^(?:phone|email|linkedin)\s*:\s*(?:\+?\s*)?$",
               " ", text, flags=re.IGNORECASE | re.MULTILINE)
    return t

# =================== NER (PERSON/ORG) =================== #

_ner_pipe = None

def _load_ner():
    """Multilingual NER (XLM-R) for PERSON/ORG, cached singleton."""
    global _ner_pipe
    if _ner_pipe is not None:
        return _ner_pipe
    from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
    model_name = "Davlan/xlm-roberta-base-ner-hrl"
    tok = AutoTokenizer.from_pretrained(model_name)
    mdl = AutoModelForTokenClassification.from_pretrained(model_name)
    _ner_pipe = pipeline("ner", model=mdl, tokenizer=tok, aggregation_strategy="simple")
    return _ner_pipe

def _extract_person_org_spans(text: str, max_chars: int = 8000) -> Tuple[List[Tuple[int,int,str]], List[Tuple[int,int,str]]]:
    """Run NER; return PERSON & ORG spans as (start, end, word)."""
    ner = _load_ner()
    snippet = text[:max_chars]
    ents = ner(snippet)
    persons, orgs = [], []
    for e in ents:
        if e.get("entity_group") == "PER":
            persons.append((int(e["start"]), int(e["end"]), e["word"]))
        elif e.get("entity_group") == "ORG":
            orgs.append((int(e["start"]), int(e["end"]), e["word"]))
    return persons, orgs

def _primary_name_from_spans(text: str, person_spans: List[Tuple[int,int,str]]) -> Optional[str]:
    if not person_spans: return None
    longest = max(person_spans, key=lambda s: s[1]-s[0])
    return text[longest[0]:longest[1]].strip()

def _build_candidate_id(text: str, email: Optional[str]) -> str:
    if email:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, email.lower()))
    basis = hashlib.sha256((text[:2000]).encode("utf-8", errors="ignore")).hexdigest()
    return str(uuid.uuid5(uuid.NAMESPACE_URL, basis))

# =================== PII & structural scrubbing =================== #

def _split_sections(text: str) -> Dict[str, str]:
    lines = text.split("\n")
    cur = "other"
    out = {k: [] for k in list(SEC_HEADERS.keys()) + ["other"]}
    for ln in lines:
        low = ln.lower().strip()
        switched = False
        for sec, pats in SEC_HEADERS.items():
            if any(re.search(p, low) for p in pats):
                cur = sec
                switched = True
                break
        if not switched:
            out[cur].append(ln)
    return {k: "\n".join(v).strip() for k, v in out.items()}

def _remove_dates_from_experience(text: str) -> str:
    """Drop lines that are clearly dates/tenures/headers; keep action/description sentences."""
    kept = []
    for ln in [l for l in text.split("\n") if l.strip()]:
        stripped = ln.lstrip()
        had_bullet = bool(re.match(r"^\s*[-•*–—]+\s*", stripped))
        low = ln.lower()
        is_datey = _MONTHS_RE.search(low) or _DURATION_RE.search(low) or _YEAR_RE.search(low)
        # header-ish lines (company — title) drop unless it's a bullet description
        headerish = ("—" in ln or " - " in ln) and not had_bullet
        if headerish or (is_datey and not had_bullet):
            continue
        kept.append(_strip_list_marker(ln))
    return "\n".join(kept)

def _scrub_pii_and_org(text: str, email: Optional[str], candidate_id: str) -> str:
    """Remove emails/phones/urls/IDs and PERSON/ORG via NER; normalize whitespace."""
    t = text
    if email: t = EMAIL_RE.sub(" ", t)
    t = PHONE_RE.sub(" ", t)
    t = URL_RE.sub(" ", t)
    t = ID_HINT_RE.sub(" ", t)
    t = t.replace(candidate_id, " ")
    # NER-based removal of names/orgs
    persons, orgs = _extract_person_org_spans(t)
    def _strip_spans(s: str, spans: List[Tuple[int,int,str]]) -> str:
        for start, end, _ in sorted(spans, key=lambda x: x[0], reverse=True):
            s = s[:start] + " " + s[end:]
        return s
    t = _strip_spans(t, persons)
    t = _strip_spans(t, orgs)
    # bullets to nothing
    t = "\n".join(_strip_list_marker(l) for l in t.split("\n"))
    # whitespace cleanup
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r" {2,}", " ", t)
    return t.strip()

# =================== LLM Backends (pluggable) =================== #

class LocalHFBackend:
    """
    Local HuggingFace backend (no API keys).
    model: e.g., "Qwen/Qwen2-7B-Instruct" or "Qwen/Qwen2-1.5B-Instruct" (lighter)
    """
    def __init__(self, model: str = "Qwen/Qwen2-1.5B-Instruct", device_map: str = "auto", dtype: str = None):
        from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
        self.tokenizer = AutoTokenizer.from_pretrained(model)
        self.model = AutoModelForCausalLM.from_pretrained(model, device_map=device_map, trust_remote_code=True)
        self.pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            do_sample=False,
            temperature=0.0,
            max_new_tokens=1024,
            repetition_penalty=1.05,
        )

    def generate_json(self, prompt: str) -> dict:
        out = self.pipe(prompt)[0]["generated_text"]
        # try to extract the last JSON block
        json_match = re.search(r"\{[\s\S]*\}\s*$", out.strip())
        if not json_match:
            # fallback: search any JSON-like
            json_match = re.search(r"\{[\s\S]*\}", out)
        if not json_match:
            raise ValueError("LLM did not return JSON.")
        return json.loads(json_match.group(0))
    

# =================== LLM Prompt (English; AR/EN content) =================== #

_PROMPT_TEMPLATE = """You are a semantic filtering engine. Task: from the provided CV sections,
KEEP ONLY lines that are relevant to the Job Description (JD). Do NOT invent text.
Work in AR/EN as needed. Return STRICT JSON matching the schema below and nothing else.

Rules (very important):
- Use ONLY the content provided in CV sections; do NOT add or rewrite content.
- For each kept line, it must be directly relevant to JD requirements (skills, tools, methods, domain).
- Drop purely soft/behavioral lines (teamwork, communication, fast learner, etc.) unless explicitly technical.
- For Experience: keep only action/description lines (titles/companies/dates are already removed).
- For Projects: keep a line ONLY if it contains at least two technical terms AND an actionable phrase (built/implemented/optimized/etc.). A numeric metric is preferred but not required.
- Ignore any personal info; PII is already removed.
- Keep lines concise; if a line is long, keep only the most informative part (but do NOT rephrase beyond deletion).
- IMPORTANT: If a section has no relevant lines, return an empty list for that section.

Schema (JSON):
{
  "skills":      ["kept line", ...],
  "experience":  ["kept line", ...],
  "education":   ["kept line", ...],
  "certifications": ["kept line", ...],
  "courses":     ["kept line", ...],
  "projects":    ["kept line", ...]
}

Now the inputs:

JD:
\"\"\"{jd}\"\"\"

CV_SKILLS:
\"\"\"{skills}\"\"\"

CV_EXPERIENCE:
\"\"\"{experience}\"\"\"

CV_EDUCATION:
\"\"\"{education}\"\"\"

CV_CERTIFICATIONS:
\"\"\"{certs}\"\"\"

CV_COURSES:
\"\"\"{courses}\"\"\"

CV_PROJECTS:
\"\"\"{projects}\"\"\"
Return STRICT JSON only.
"""

# =================== Public API =================== #

def parse_resume_with_llm(
    raw_text: str,
    job_desc: str,
    llm_backend,
    llm_model: Optional[str] = None,
    write_outputs: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Pipeline:
      1) Normalize → extract email/name/id → split sections
      2) Remove dates/tenures from experience
      3) PII & ORG scrubbing (NER + regex)
      4) LLM semantic filtering against JD
      5) Build comparison_text from LLM-kept lines only (all sections)
    """
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be a string containing CV text")
    if not isinstance(job_desc, str) or not job_desc.strip():
        raise ValueError("job_desc must be a non-empty string")

    # 1) normalize and extract identifiers
    text = _normalize_text(raw_text)
    email = EMAIL_RE.search(text)
    email_val = email.group(0) if email else None
    persons, orgs = _extract_person_org_spans(text)
    name = _primary_name_from_spans(text, persons)
    candidate_id = _build_candidate_id(text, email_val)

    # 2) split sections and pre-clean experience dates
    secs = _split_sections(text)
    skills_raw   = secs.get("skills", "")
    exp_raw      = _remove_dates_from_experience(secs.get("experience", ""))
    edu_raw      = secs.get("education", "")
    certs_raw    = secs.get("certifications", "")
    courses_raw  = secs.get("courses", "")
    projects_raw = secs.get("projects", "")

    # 3) PII/ORG scrub per section (defense-in-depth); remove list markers
    def _scrub(s: str) -> str:
        return _scrub_pii_and_org(s, email_val, candidate_id)

    skills_s   = _scrub(skills_raw)
    exp_s      = _scrub(exp_raw)
    edu_s      = _scrub(edu_raw)
    certs_s    = _scrub(certs_raw)
    courses_s  = _scrub(courses_raw)
    projects_s = _scrub(projects_raw)

    # 4) LLM semantic filtering
    prompt = _PROMPT_TEMPLATE.format(
        jd=_fmt_escape(job_desc.strip()),
        skills=_fmt_escape(skills_s.strip()),
        experience=_fmt_escape(exp_s.strip()),
        education=_fmt_escape(edu_s.strip()),
        certs=_fmt_escape(certs_s.strip()),
        courses=_fmt_escape(courses_s.strip()),
        projects=_fmt_escape(projects_s.strip()),
    )


    # init backend
    if isinstance(llm_backend, str):
        if llm_backend.lower() == "local":
            backend = LocalHFBackend(model=llm_model or "Qwen/Qwen2-1.5B-Instruct")
        else:
            raise ValueError("Unknown llm_backend string. Use 'local' or 'openai'.")
    else:
        backend = llm_backend  # assume a compatible object with .generate_json(prompt)

    try:
        llm_json = backend.generate_json(prompt)
    except Exception as e:
        raise RuntimeError(f"LLM filtering failed: {e}")

    # 5) Build comparison_text only from kept lines (no PII & no bullets)
    def _pack_list(key: str) -> List[str]:
        vals = llm_json.get(key, [])
        if not isinstance(vals, list): return []
        cleaned = []
        for v in vals:
            if isinstance(v, str) and v.strip():
                cleaned.append(_strip_list_marker(v.strip()))
        return cleaned


    kept_skills  = _pack_list("skills")
    kept_exp     = _pack_list("experience")
    kept_edu     = _pack_list("education")
    kept_certs   = _pack_list("certifications")
    kept_courses = _pack_list("courses")
    kept_proj    = _pack_list("projects")

    comparison_text = "\n\n".join(
        s for s in [
            "\n".join(kept_skills) if kept_skills else "",
            "\n".join(kept_exp) if kept_exp else "",
            "\n".join(kept_edu) if kept_edu else "",
            "\n".join(kept_certs) if kept_certs else "",
            "\n".join(kept_courses) if kept_courses else "",
            "\n".join(kept_proj) if kept_proj else "",
        ] if s
    ).strip()

    # Final safety scrub (no PII; should be already clean, but double-safety)
    comparison_text = _scrub_pii_and_org(comparison_text, email_val, candidate_id)

    result = {
        "candidate_id": candidate_id,
        "name": name,
        "email": email_val,
        "comparison_text": comparison_text,
    }

    if write_outputs:
        if path := write_outputs.get("json"):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        if path := write_outputs.get("text"):
            with open(path, "w", encoding="utf-8") as f:
                f.write(comparison_text)

    return result


raw_cv   = """Mansor Saud Alshamran
Curriculum Vitae / سيرة ذاتية

Personal Information
Phone: +966 54 144 1537
Email: m.alshamran.cs@gmail.com
LinkedIn: https://www.linkedin.com/in/mansor-alshamran-948b1a27a/

Target Position
Data Scientist / Data Analyst

Professional Summary
Highly motivated Data Scientist and Analyst with a strong foundation in computer science,
machine lear-
ning and data analysis. Experienced in building predictive models, developing deep learning
architectures, and analyzing datasets to extract insights. Co-founder with entrepreneurial
experience in launching online businesses. References available upon request.

Technical Skills
- Programming: Python, NumPy, Pandas
- Machine Learning: scikit-learn, Regression, Classification, SVM
- Deep Learning: TensorFlow, Keras, Neural Networks, PCA
- Data Analysis & Visualization
- Problem Solving, Fast Learning, Team Collaboration

Work Experience
Solutions by STC — System Engineer
Aug 2023 – Nov 2023 (3 months)
- Supported IT infrastructure and system operations ensuring efficiency and reliability.

Perfect Presentation (2P) — Ministry of Health Call Center
May 2022 – Sep 2022 (5 months)
- Provided technical and customer support, ensuring smooth operations at MOH call center.

Co-Founder & CEO — Fabrikent (3D Printing Online Store)
Founder — Driemor (Health & Beauty Online Store)

Education
Prince Sattam Bin Abdulaziz University — Bachelor of Computer Science
GPA: 4.48 / 5 — Second Class Honors

Certifications & Training
- AI Concepts and Advanced Applications — Samai
- IBM Machine Learning with Python
- IBM Introduction to Deep Learning with Keras
- Tuwaiq Academy — AI Models Bootcamp (In Progress)

Projects
- Saudi E-commerce Dataset Analysis: Analyzed impact of sales channels on ratings & reviews.
- Multiple Sclerosis Diagnosis: Built MRI image classifier with PCA achieving 96% accuracy.
- TikTakToe Bot: Simple X/O bot implementation.
- Tuwaiq Chatbot: Developed a chatbot to answer academy-related queries.
- Breast Cancer Classification: Neural network analysis of dataset (Accuracy: 38%).
- Seattle House Prices: Neural network prediction model (Accuracy: 84%).
- Study Hours vs Scores: Linear regression achieving 98% accuracy.
- California Housing Prices: Neural network (73%) & SVM (79%) models.
"""

job_desc = """Develop and deploy predictive models using machine learning and deep learning frameworks (e.g., TensorFlow, Keras, scikit-learn).

Perform data analysis and visualization to generate insights for decision making.

Work with large datasets to build classification and regression models.

Optimize model performance with techniques such as PCA, SVM, and neural networks.

Support the design of ETL pipelines and ensure data quality.

Collaborate with business stakeholders to translate requirements into data-driven solutions.

Document results and present findings clearly.

Requirements:

Bachelor’s degree in Computer Science, Statistics, or related field.

Strong programming skills in Python, with experience in libraries like NumPy and Pandas.

Hands-on experience with machine learning algorithms (classification, regression, clustering).

Familiarity with deep learning frameworks such as TensorFlow and Keras.

Strong analytical skills with experience in data visualization tools (e.g., Power BI, Matplotlib, Seaborn).

Knowledge of SQL for data extraction and manipulation.

Excellent problem-solving abilities and the ability to work in a fast-paced environment.

Preferred:

Experience with healthcare or e-commerce datasets.

Prior exposure to building and deploying chatbots or recommendation systems.

Certifications in AI or ML (e.g., IBM, Tuwaiq Academy, or similar)."""

backend = LocalHFBackend(model="Qwen/Qwen2-1.5B-Instruct")
out = parse_resume_with_llm(raw_cv, job_desc, llm_backend=backend)

print(out["candidate_id"], out["name"], out["email"])
print(out["comparison_text"])