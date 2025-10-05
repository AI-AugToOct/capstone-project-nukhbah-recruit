# FastAPI placeholder app for CV + Company input
# - Pure placeholders (no backend processing)
# - Simple HTML with minimal CSS/JS inline
# - English labels as requested, success text exactly: "Resume sent successfuly"

from fastapi import FastAPI, UploadFile, Form, Request
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from typing import Optional, List

app = FastAPI(title="Recruitment MVP")

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ---------- Shared tiny CSS & JS ----------
BASE_STYLE = """
<style>
  :root { --bg:#0f172a; --card:#111827; --text:#e5e7eb; --muted:#94a3b8; --accent:#22d3ee; }
  * { box-sizing: border-box; font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial; }
  body { margin:0; background:linear-gradient(180deg,#0b1220,#0f172a); color:var(--text); }
  .wrap { max-width: 760px; margin: 48px auto; padding: 0 16px; }
  .card {
    background: rgba(255, 255, 255, 0.1); /* لون أبيض شفاف */
    border-radius: 12px; 
    padding: 20px;
    backdrop-filter: blur(10px); /* هذا يسوي الضبابية */
    -webkit-backdrop-filter: blur(10px); /* لدعم Safari */
  }
  h1 { margin: 0 0 8px; font-size: 28px; }
  p.lead { color: var(--muted); margin-top: 0; }
  .grid { display:grid; gap:16px; }
  .row { display:flex; gap:12px; flex-wrap:wrap; align-items:center; }
  label { font-size:14px; color: var(--muted); display:block; margin-bottom:6px; }
  input[type="text"], textarea, input[type="file"], select {
    width:100%; padding:12px 14px; color:var(--text); background:#0b1220; border:1px solid #263043; border-radius:12px; outline:none;
  }
  .logo {
    position: absolute;
    top: 10px;
    right: 10px;
    width: 120px;
  }
  textarea { min-height: 140px; resize: vertical; }
  .btn {
    background: var(--accent); color:#001015; border:none; padding:12px 18px; border-radius:12px;
    font-weight: 700; cursor: pointer; transition: transform .05s ease-in-out;
  }
  .btn:hover { transform: translateY(-5px); }
  .btn.secondary { background:#1f2937; color:var(--text); }
  .choices { display:grid; gap:10px; margin-top:4px; }
  .error { color:#fca5a5; font-size:14px; }
  .success { color:#34d399; font-size:16px; font-weight:700; }
  .chips { display:flex; gap:8px; flex-wrap:wrap; }
  .chip { background:#0b1220; border:1px solid #233046; color:#a5b4fc; padding:6px 10px; border-radius:999px; font-size:12px; }
  .spacer { height:8px; }
  .center { text-align:center; }
</style>
<script>
  // Enforce exactly one checkbox in the "role" group + toggle CSV upload for AI Engineer
  function singleCheck(el){
    const boxes = document.querySelectorAll('input[name="role"]');
    boxes.forEach(b => { if(b !== el) b.checked = false; });

    // Toggle CSV upload visibility
    const up = document.getElementById('ai-dataset');
    if (up){
      if (el.checked && el.value === 'AI Engineer') {
        up.style.display = 'block';
      } else {
        up.style.display = 'none';
        const file = document.getElementById('dataset_csv');
        if (file) file.value = ''; // reset if user switches role
      }
    }
  }
</script>
"""

# ---------- Pages ----------

@app.get("/", response_class=HTMLResponse)
def landing():
    return f"""
    <!doctype html><html><head><meta charset="utf-8"><title>Recruitment MVP</title>{BASE_STYLE}</head><body>
      <img src="/static/nukhbah.png" alt="Nukhbah Logo" class="logo">
      <div class="wrap">
        <div class="card">
          <h1>Welcome</h1>
          <p class="lead">Are you an individual or a company?</p>
          <div class="row">
            <a class="btn secondary" href="/individual">I am an individual</a>
            <a class="btn secondary" href="/company">I am a company</a>
          </div>
          <div class="spacer"></div>
        </div>
      </div>
    </body></html>
    """

# ---- Individual flow ----

@app.get("/individual", response_class=HTMLResponse)
def individual_form():
    return f"""
    <!doctype html><html><head><meta charset="utf-8"><title>Upload Resume</title>{BASE_STYLE}</head><body>
      <img src="/static/nukhbah.png" alt="Nukhbah Logo" class="logo">
      <div class="wrap">
        <div class="card">
          <h1>Upload your resume</h1>
          <form class="grid" action="/individual/submit" method="post" enctype="multipart/form-data">
            <div>
              <label for="resume">Resume (PDF)</label>
              <input id="resume" name="resume" type="file" accept=".pdf,.txt" required>
            </div>
            <div class="row">
              <button class="btn" type="submit">Send resume</button>
              <a class="btn secondary" href="/">Back</a>
            </div>
          </form>
        </div>
      </div>
    </body></html>
    """

@app.post("/individual/submit", response_class=HTMLResponse)
async def individual_submit(resume: UploadFile):
    # Placeholder: ignore file content; just show success message
    filename = resume.filename if resume else "file"
    return f"""
    <!doctype html><html><head><meta charset="utf-8"><title>Success</title>{BASE_STYLE}</head><body>
      <img src="/static/nukhbah.png" alt="Nukhbah Logo" class="logo">
      <div class="wrap">
        <div class="card center">
          <h1>Done</h1>
          <p class="success">Resume sent successfuly</p>
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
    <!doctype html><html><head><meta charset="utf-8"><title>Company Intake</title>{BASE_STYLE}</head><body>
      <img src="/static/nukhbah.png" alt="Nukhbah Logo" class="logo">
      <div class="wrap">
        <div class="card">
          <h1>Company intake</h1>
          <p class="lead">Fill in your company details and role focus.</p>
          {error_html}
          <form class="grid" action="/company/submit" method="post">
            <div>
              <label for="company_name">company name</label>
              <input id="company_name" name="company_name" type="text" placeholder="e.g., SDAIA, SITE" required>
            </div>
            <div>
              <label for="sector">sector</label>
              <input id="sector" name="sector" type="text" placeholder="e.g., Healthcare, E-commerce" required>
            </div>
            <div>
              <label>role (choose one via checkbox)</label>
              <div class="choices">
                <label><input type="checkbox" name="role" value="AI Engineer" onchange="singleCheck(this)"> AI Engineer</label>
                <label><input type="checkbox" name="role" value="Software Engineer" onchange="singleCheck(this)"> Software Engineer</label>
                <label><input type="checkbox" name="role" value="Cloud Engineer" onchange="singleCheck(this)"> Cloud Engineer</label>
                <label><input type="checkbox" name="role" value="Cyber Security" onchange="singleCheck(this)"> Cyber Security</label>
                <label><input type="checkbox" name="role" value="Fullstack Developer" onchange="singleCheck(this)"> Fullstack Developer</label>
              </div>
              <p class="lead" style="margin-top:8px;">(Only one checkbox can be selected.)</p>
            </div>
            <!-- AI Engineer dataset (CSV) — hidden by default -->
            <div id="ai-dataset" style="display:none;">
            <label for="dataset_csv">dataset (CSV) for test generation</label>
            <input id="dataset_csv" name="dataset_csv" type="file" accept=".csv">
            </div>
            <div>
              <label for="job_description">job description</label>
              <textarea id="job_description" name="job_description" placeholder="Specify the teqnical details of the role, avoid unnessesary details like salary, location, etc." required></textarea>
            </div>
            <div class="row">
              <button class="btn" type="submit">OK, Send</button>
              <a class="btn secondary" href="/">Back</a>
            </div>
          </form>
        </div>
      </div>
    </body></html>
    """

@app.post("/company/submit", response_class=HTMLResponse)
async def company_submit(
    request: Request,
    company_name: str = Form(...),
    sector: str = Form(...),
    role: Optional[List[str]] = Form(None),  # multiple checkboxes may arrive; we enforce one
    job_description: str = Form(...)
):
    # Server-side guard: enforce exactly one role selected
    selected = role or []
    if len(selected) != 1:
        # redirect back with error message
        return company_form(error="Please select exactly one role (checkbox).")

    # Placeholder: no persistence. Just echo a success screen
    role_val = selected[0]
    return f"""
    <!doctype html><html><head><meta charset="utf-8"><title>Received</title>{BASE_STYLE}</head><body>
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
          </div>
          <div class="spacer"></div>
          <div class="row">
            <a class="btn" href="/">Home</a>
            <a class="btn secondary" href="/company">New company</a>
          </div>
        </div>
      </div>
    </body></html>
    """

# ---- Health check (for future deployment probing) ----
@app.get("/healthz")
def healthz():
    return PlainTextResponse("ok")
