# embeddings + cosine similarity 

import json
from sentence_transformers import SentenceTransformer, util
from src.config_candidate import SIMILARITY_THRESHOLD, CHUNK_SIZE, OVERLAP

#  Load model once globally 
model = SentenceTransformer("lwolfrum2/careerbert-jg")


def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
    words = text.split()
    if not words:
        return []
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = words[i:i + chunk_size]
        if len(chunk) < chunk_size:  # padding if CV text less than job description
            chunk += ["[PAD]"] * (chunk_size - len(chunk))
        chunks.append(" ".join(chunk))
    return chunks


def match_candidates(cvs_data, job_description: str, job_field: str, output_path: str = "qualified_candidates.json"):
    # Load CVs
    if isinstance(cvs_data, str):
        with open(cvs_data, "r", encoding="utf-8") as f:
            cvs_data = json.load(f)

    if not isinstance(cvs_data, list):
        raise ValueError("cvs_data must be a list of dictionaries")

    # Load Job description and field
    if not job_description and not job_field:
        raise ValueError("Job info must contain job_description or job_field")

    job_text = f"{job_field} {job_description}".strip()

    # Encode job description chunks
    jd_chunks = chunk_text(job_text)
    jd_embeddings = model.encode(jd_chunks, convert_to_tensor=True)

    qualified_candidates = []

    for cv_data in cvs_data:
        if not isinstance(cv_data, dict):
            continue

        cv_sections = []

        # Summary
        summary = cv_data.get("summary", "")
        if summary:
            cv_sections.append(summary)

        # Experience
        experience = []
        for exp in cv_data.get("work_experience", []):
            responsibilities = exp.get("responsibilities", [])
            if isinstance(responsibilities, list):
                experience.extend(responsibilities)
        cv_sections.append(" ".join(experience))

        # Technical skills
        skills_list = cv_data.get("technical_skills", [])
        if isinstance(skills_list, list):
            cv_sections.append(" ".join(skills_list))

        # Education
        education_list = []
        for edu in cv_data.get("education", []):
            degree = edu.get("degree", "")
            field = edu.get("field", "")
            if degree or field:
                education_list.append(f"{degree} {field}".strip())
        cv_sections.append(" ".join(education_list))

        # Certifications
        certs_list = [cert.get("name", "") for cert in cv_data.get("certifications", [])]
        cv_sections.append(" ".join(certs_list))

        # Projects
        projects_list = [f"{proj.get('name','')} {proj.get('description','')}" 
                         for proj in cv_data.get("projects", [])]
        cv_sections.append(" ".join(projects_list))

        # Soft skills
        soft_skills = cv_data.get("soft_skills", [])
        if isinstance(soft_skills, list):
            cv_sections.append(" ".join(soft_skills))

        # Languages
        langs = [f"{lang.get('language','')} {lang.get('proficiency','')}" for lang in cv_data.get("languages", [])]
        cv_sections.append(" ".join(langs))

        # Interests
        interests = cv_data.get("interests", [])
        if isinstance(interests, list):
            cv_sections.append(" ".join(interests))

        cv_text = " ".join([section for section in cv_sections if section.strip()])
        if not cv_text.strip():
            continue

        # Encode CV chunks
        cv_chunks = chunk_text(cv_text, chunk_size=CHUNK_SIZE, overlap=OVERLAP)
        cv_embeddings = model.encode(cv_chunks, convert_to_tensor=True)

        # cosine similarity
        similarity_matrix = util.cos_sim(cv_embeddings, jd_embeddings)
        max_per_cv_chunk = similarity_matrix.max(dim=1).values
        final_similarity = max_per_cv_chunk.mean().item()

        candidate_name = cv_data.get("name", "Unknown")

        if final_similarity >= SIMILARITY_THRESHOLD:
            qualified_candidates.append({
                "full_name": candidate_name,
                "email": cv_data.get("contact", {}).get("email", ""),
                "similarity_score": round(final_similarity, 3)
            })

    # Sort candidates
    qualified_candidates = sorted(qualified_candidates, key=lambda x: x["similarity_score"], reverse=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(qualified_candidates, f, ensure_ascii=False, indent=4)

    return qualified_candidates

# Inputs:
#        1. cv_json_path: JSON file with CVs (list of candidates).
#        2. job_title 
#        3. job_description
#        output_path: file to save qualified candidates.
# output: json file contain List of qualified candidates sorted by similarity score.
 
