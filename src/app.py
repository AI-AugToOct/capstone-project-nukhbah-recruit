# FastAPI placeholder app for CV + Company input
from fastapi import FastAPI, UploadFile, Form, Request, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, PlainTextResponse
from src.candidate_matching import match_candidates
from main import extract_cvs as pipeline_extract_cvs
from main import main as pipeline_main
from src.evaluate_quiz import evaluate_answer
import json
from pathlib import Path
from typing import Optional, List
import shutil
import logging

app = FastAPI(title="Recruitment MVP")

STATIC_DIR = Path(__file__).parent / "static"
UPLOADS_DIR = Path(__file__).parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

# ---------- Shared tiny CSS & JS ----------
BASE_STYLE = """
<style>
  :root { 
    --bg:#f6f6e9; 
    --card:#97ab9d; 
    --text:#01290c; 
    --muted:#3a4a3e; 
    --accent:#01290c; 
  }
  * { box-sizing: border-box; font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial; }
  body { margin:0; background:var(--bg); color:var(--text); }

  .wrap { max-width: 760px; margin: 80px auto; padding: 0 16px; }

  .card {
    background: var(--card);
    border-radius: 12px; 
    padding: 20px;
    box-shadow: 0 4px 10px rgba(1,41,12,0.1);
    border: 1px solid rgba(1,41,12,0.15);
  }

  h1 { margin: 0 0 8px; font-size: 28px; color: var(--accent); }
  p.lead { color: var(--text); margin-top: 0; }

  .grid { display:grid; gap:16px; }
  .row { display:flex; gap:12px; flex-wrap:wrap; align-items:center; }

  label { font-size:14px; color: var(--muted); display:block; margin-bottom:6px; }

  input[type="text"], input[type="email"], textarea, input[type="file"], select {
    width:100%; padding:12px 14px; color:var(--text); 
    background:#f1f5f2; border:1px solid #97ab9d; border-radius:12px; outline:none;
  }

  textarea { min-height: 140px; resize: vertical; }

  .btn {
    background: var(--accent); color:#f6f6e9; border:none; 
    padding:12px 18px; border-radius:12px;
    font-weight:700; cursor:pointer; transition: transform .05s ease-in-out;
  }

  .btn:hover { transform: translateY(-3px); background:#024d17; }

  .btn.secondary { background:#97ab9d; color:var(--text); }

  .choices { display:grid; gap:10px; margin-top:4px; color:var(--text); }

  .error { color:#b91c1c; font-size:14px; }
  .success { color:#024d17; font-size:16px; font-weight:700; }

  .spacer { height:8px; }
  .center { text-align:center; }

  /* 🔹 Navigation bar */
  .navbar {
    position: fixed;
    top: 0; left: 0; right: 0;
    background: var(--accent);
    color:#f6f6e9;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 24px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    z-index: 100;
  }

  .navbar .logo {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .navbar img {
    width: 30px;
    height: 30px;
    border-radius:50%;
  }

  .navbar h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 700;
    color: #f6f6e9;
  }

  .nav-links {
    display: flex;
    gap: 16px;
  }

  .nav-links a {
    color: #f6f6e9;
    text-decoration: none;
    font-weight: 600;
    transition: opacity 0.2s ease;
  }

  .nav-links a:hover {
    opacity: 0.8;
  }

  textarea.code {
    font-family: monospace;
    background:#f1f5f2;
    color:var(--text);
    min-height:200px;
    border-radius:12px;
    padding:12px;
    border:1px solid #97ab9d;
  }

  pre.code-output {
    background:#f1f5f2;
    color:var(--text);
    padding:12px;
    border-radius:12px;
    text-align:left;
    border:1px solid #97ab9d;
  }
</style>
"""


# ---------- Small helper: save UploadFile to disk ----------
def _save_upload(file: UploadFile, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / file.filename
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    file.file.close()
    return dest

# ---------- Pages ----------

def navbar_html():
    return """
    <nav class="navbar">
        <div class="logo">
          <img src="/static/nukhbah.jpg" alt="Nukhbah Logo">
          <h2>Nukhbah Recruitment</h2>
        </div>
        <div class="nav-links">
          <a href="/individual">Individual</a>
          <a href="/company">Company</a>
          <a href="/quiz">Quiz</a>
        </div>
    </nav>
    """

@app.get("/", response_class=HTMLResponse)
def landing():
    return f"""
    <!doctype html><html><head><meta charset="utf-8"><title>Nukhbah Recruitment</title>{BASE_STYLE}</head><body>
      {navbar_html()}
      <div class="wrap">
        <div>
          <h1>Welcome to Nukhbah Recruitment</h1>
        <p></p>
        </div>
      </div>
    </body></html>
    """

# ---- Individual flow ----

@app.get("/individual", response_class=HTMLResponse)
def individual_form():
    return f"""
    <!doctype html><html><head><meta charset="utf-8"><title>Upload Resume</title>{BASE_STYLE}</head><body>
      {navbar_html()}
      <div class="wrap">
        <div class="card">
          <h1>Upload your resume</h1>
          <form class="grid" action="/individual/submit" method="post" enctype="multipart/form-data">
            <div>
              <label for="resume">Resume (PDF)</label>
              <input id="resume" name="resume" type="file" accept=".pdf,.txt" required>
            </div>
            <div class="row">
              <button class="btn secondary" type="submit">Send resume</button>
              <a class="btn secondary" href="/">Back</a>
            </div>
          </form>
        </div>
      </div>
    </body></html>
    """

@app.post("/individual/submit", response_class=HTMLResponse)
async def individual_submit(resume: UploadFile):
    filename = resume.filename if resume else "file"
    try:
        saved_path = _save_upload(resume, UPLOADS_DIR)
        logger.info("Saved CV to %s", saved_path)
        app.state.last_cv_files = [str(saved_path)]
    except Exception as e:
        logger.exception("Failed saving upload")
        return HTMLResponse(f"<h3>Failed to save file: {e}</h3>", status_code=500)

    try:
        cv_json_path = pipeline_extract_cvs([str(saved_path)])
        logger.info("CV extraction invoked successfully -> %s", cv_json_path)
    except Exception:
        pass

    return f"""
    <!doctype html><html><head><meta charset="utf-8"><title>Success</title>{BASE_STYLE}</head><body>
      {navbar_html()}
      <div class="wrap">
        <div class="card center">
          <h1>Done</h1>
          <p class="success">Resume sent successfully</p>
          <p class="lead">File received: <b>{filename}</b></p>
          <div class="row" style="justify-content:center">
            <a class="btn" href="/">Home</a>
          </div>
        </div>
      </div>
    </body></html>
    """

# ---- Company flow ----
@app.get("/company", response_class=HTMLResponse)
def company_form(error: Optional[str] = None):
    error_html = f'<p class="error">{error}</p>' if error else ""
    return f"""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Company Intake</title>
        {BASE_STYLE}
    </head>
    <body>
        {navbar_html()}
        <div class="wrap">
            <div class="card">
                <h1>Company Intake</h1>
                <p class="lead">Fill in your company details and role focus.</p>
                {error_html}
                <form class="grid" action="/company/submit" method="post" enctype="multipart/form-data">
                    <div>
                        <label for="company_name">Company Name</label>
                        <input id="company_name" name="company_name" type="text" placeholder="e.g., SDAIA, SITE" required>
                    </div>
                    <div>
                        <label for="sector">Sector</label>
                        <input id="sector" name="sector" type="text" placeholder="e.g., Healthcare, E-commerce" required>
                    </div>
                    <div>
                        <label>Role (choose one via checkbox)</label>
                        <div class="choices">
                            <label><input type="checkbox" name="role" value="AI Engineer" onchange="singleCheck(this)"> AI Engineer</label>
                            <label><input type="checkbox" name="role" value="Software Engineer" onchange="singleCheck(this)"> Software Engineer</label>
                            <label><input type="checkbox" name="role" value="Cloud Engineer" onchange="singleCheck(this)"> Cloud Engineer</label>
                            <label><input type="checkbox" name="role" value="Cyber Security" onchange="singleCheck(this)"> Cyber Security</label>
                            <label><input type="checkbox" name="role" value="Fullstack Developer" onchange="singleCheck(this)"> Fullstack Developer</label>
                        </div>
                        <p class="lead" style="margin-top:8px;">(Only one checkbox can be selected.)</p>
                    </div>
                    <div id="ai-dataset" style="display:none;">
                        <label for="dataset_csv">Dataset (CSV) for test generation</label>
                        <input id="dataset_csv" name="dataset_csv" type="file" accept=".csv">
                    </div>
                    <div>
                        <label for="job_description">Job Description</label>
                        <textarea id="job_description" name="job_description" placeholder="Specify the technical details of the role, avoid unnecessary details like salary, location, etc." required></textarea>
                    </div>
                    <div class="row">
                        <button class="btn" type="submit">OK, Send</button>
                        <a class="btn secondary" href="/">Back</a>
                    </div>
                </form>
            </div>
        </div>
    </body>
    </html>
    """

@app.post("/company/submit", response_class=HTMLResponse)
async def company_submit(
    request: Request,
    company_name: str = Form(...),
    sector: str = Form(...),
    role: Optional[List[str]] = Form(None),
    job_description: str = Form(...),
    dataset_csv: UploadFile | None = File(None),
):
    # enforce exactly one role
    selected = role or []
    if len(selected) != 1:
        return company_form(error="Please select exactly one role (checkbox).")
    role_val = selected[0]

    # save CSV only if role == AI Engineer and a file provided
    dataset_path_str = None
    if role_val == "AI Engineer" and dataset_csv and dataset_csv.filename:
        try:
            saved_ds = _save_upload(dataset_csv, UPLOADS_DIR)
            dataset_path_str = str(saved_ds)
            logger.info("Saved dataset CSV to %s", saved_ds)
        except Exception as e:
            logger.exception("Failed saving dataset CSV")
            return HTMLResponse(f"<h3>Failed to save dataset CSV: {e}</h3>", status_code=500)

    # call main pipeline
    try:
        cv_list = getattr(app.state, "last_cv_files", None)
        pipeline_main(
            job_description=job_description,
            sector=sector,
            job_field=role_val,
            cv_files=cv_list,
            data_path=dataset_path_str
        )
        logger.info("Pipeline main() invoked successfully")
    except Exception as e:
        logger.exception("pipeline_main failed")
        pass

    return f"""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Received</title>
        {BASE_STYLE}
    </head>
    <body>
        <img src="/static/nukhbah.png" alt="Nukhbah Logo" class="logo">
        <div class="wrap">
            <div class="card">
                <h1>Submission received</h1>
                <p class="success">Your company info was received (placeholder).</p>
                <div class="grid">
                    <div><label>company name</label><div>{company_name}</div></div>
                    <div><label>sector</label><div>{sector}</div></div>
                    <div><label>role</label><div>{role_val}</div></div>
                    <div><label>job description</label><div><pre style="white-space:pre-wrap">{job_description}</pre></div></div>
                    {"<div><label>dataset</label><div>"+dataset_csv.filename+"</div></div>" if dataset_path_str else ""}
                </div>
                <div class="spacer"></div>
                <div class="row">
                    <a class="btn" href="/">Home</a>
                    <a class="btn secondary" href="/company">New company</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

# ---- Quiz flow ----

@app.get("/quiz", response_class=HTMLResponse)
def quiz_entry_form():
    return f"""
    <!doctype html><html><head><meta charset="utf-8"><title>Quiz Login</title>{BASE_STYLE}</head><body>
      {navbar_html()}
      <div class="wrap">
        <div class="card">
          <h1>Quiz Access</h1>
          <p class="lead">Enter your name and email to start the quiz.</p>
          <form class="grid" action="/quiz/start" method="post">
            <div>
              <label for="full_name">Full name</label>
              <input id="full_name" name="full_name" type="text" required>
            </div>
            <div>
              <label for="email">Email</label>
              <input id="email" name="email" type="email" required>
            </div>
            <div class="row">
              <button class="btn" type="submit">Start Quiz</button>
              <a class="btn secondary" href="/">Back</a>
            </div>
          </form>
        </div>
      </div>
    </body></html>
    """

@app.post("/quiz/start", response_class=HTMLResponse)
async def quiz_start(full_name: str = Form(...), email: str = Form(...)):
    try:
        with open("qualified_candidates.json", "r", encoding="utf-8") as f:
            candidates = json.load(f)
        exists = any(
            c.get("contact", {}).get("email", "").lower() == email.lower()
            or c.get("full_name", "").lower() == full_name.lower()
            for c in candidates
        )
    except Exception as e:
        return HTMLResponse(f"<h3>Error loading candidates: {e}</h3>", status_code=500)

    if not exists:
        return HTMLResponse(
            f"<h3 style='color:red;'>You are not listed as a qualified candidate.</h3>"
            f"<p><a href='/quiz'>Back</a></p>", status_code=403
        )

    try:
        with open("generated_quiz.json", "r", encoding="utf-8") as f:
            quiz_data = json.load(f)
    except FileNotFoundError:
        return HTMLResponse("<h3>No quiz available. Please try again later.</h3>", status_code=404)

    quiz_text = quiz_data if isinstance(quiz_data, str) else json.dumps(quiz_data, indent=4, ensure_ascii=False)

    return f"""
    <!doctype html><html><head><meta charset="utf-8"><title>Quiz</title>{BASE_STYLE}</head><body>
      {navbar_html()}
      <div class="wrap">
        <div class="card">
          <h1>Quiz</h1>
          <p class="lead">Please read the question below and submit your code solution.</p>
          <pre style="background:#111827; padding:12px; border-radius:12px;">{quiz_text}</pre>
          <form class="grid" action="/quiz/submit" method="post">
            <input type="hidden" name="full_name" value="{full_name}">
            <input type="hidden" name="email" value="{email}">
            <label for="answer">Your code answer:</label>
            <textarea id="answer" name="answer" class="code" placeholder="Write your Python code here..." required></textarea>
            <div class="row">
              <button class="btn" type="submit">Submit Answer</button>
              <a class="btn secondary" href="/">Cancel</a>
            </div>
          </form>
        </div>
      </div>
    </body></html>
    """

@app.post("/quiz/submit", response_class=HTMLResponse)
async def quiz_submit(full_name: str = Form(...), email: str = Form(...), answer: str = Form(...)):
    try:
        with open("generated_quiz.json", "r", encoding="utf-8") as f:
            quiz_data = json.load(f)
        sector = "software_engineer"
        result = evaluate_answer(quiz_data, answer, sector)
    except Exception as e:
        return HTMLResponse(f"<h3>Error evaluating answer: {e}</h3>", status_code=500)

    return f"""
    <!doctype html><html><head><meta charset="utf-8"><title>Result</title>{BASE_STYLE}</head><body>
      {navbar_html()}
      <div class="wrap">
        <div class="card center">
          <h1>Submission received</h1>
          <p class="lead">Thank you <b>{full_name}</b>, your quiz answer has been evaluated.</p>
          <pre class="code-output">{json.dumps(result, indent=4, ensure_ascii=False)}</pre>
          <div class="row" style="justify-content:center">
            <a class="btn" href="/">Home</a>
          </div>
        </div>
      </div>
    </body></html>
    """

@app.get("/healthz")
def healthz():
    return PlainTextResponse("ok")
