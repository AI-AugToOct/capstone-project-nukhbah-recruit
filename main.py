from pathlib import Path
import json
from config import Config
from src.cv_extractor import CVExtractor
from src.cv_extractor import extract_cvs
from src.generate_gpt_quiz import gpt_quiz
from src.job_desc_samples import ai_description, cyber_security_description, software_engineering_description, cloud_engineering_description
import logging
from src.candidate_matching import match_candidates
from src.evaluate_quiz import evaluate_answer
# from src.cv_extractor import extract_cvs
from src.cv_extractor import CVExtractor
from openai import OpenAI
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
import requests

config = Config('.env')

# Your n8n webhook URL
N8N_WEBHOOK_URL = "https://mansoralshamran.app.n8n.cloud/webhook-test/aafe3615-630a-4dc9-8faf-f93e4abb6248"

def send_to_n8n(candidates_list):
    """Send qualified candidates to n8n webhook"""
    payload = {"candidates": candidates_list}
    try:
        response = requests.post(
            N8N_WEBHOOK_URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload)
        )
        if response.status_code == 200:
            logger.info(" Successfully sent candidates to n8n")
        else:
            logger.warning(f"Failed to send to n8n, status code: {response.status_code}")
            logger.warning(f"n8n response: {response.text}")
    except Exception as e:
        logger.error(f"Error connecting to n8n: {e}")


def main(job_description: str, sector: str, job_field: str,cv_files=None, data_path: str = None):
    all_cvs_file = Path("cv_extraction_output/all_extracted_cvs.json")
    all_cvs_file.parent.mkdir(parents=True, exist_ok=True)

    cvs_data = []


    # 1️⃣ Extract CVs and merge automatically with existing ones
    if cv_files:
        logger.info("Extracting and merging CVs from files: %s", cv_files)
        all_cvs_data = extract_cvs(cv_files)
        logger.info("Total CVs after extraction and merge: %d", len(all_cvs_data))
    else:
        # Load existing CVs if no new files provided
        if all_cvs_file.exists():
            with open(all_cvs_file, 'r', encoding='utf-8') as f:
                all_cvs_data = json.load(f)
            logger.info("Loaded %d existing CVs", len(all_cvs_data))
        else:
            all_cvs_data = {}
            logger.warning("No CV files provided and no existing CVs found.")

    # Match candidates to job description
    qualified_candidates = match_candidates(
        cvs_data=list(all_cvs_data.values()),
        job_description=job_description,
        job_field=job_field,
        output_path="qualified_candidates.json"
    )
    logger.info("Total qualified candidates: %d", len(qualified_candidates))

    # Save qualified candidates JSON for later stages
    with open("qualified_candidates.json", "w", encoding="utf-8") as f:
        json.dump(qualified_candidates, f, ensure_ascii=False, indent=4)
    
    # Send qualified candidates to n8n
    if qualified_candidates:
        n8n_candidates = [
            {
                "full_name": c.get("full_name"),
                "email": c.get("email"),
            } for c in qualified_candidates
        ]
        send_to_n8n(n8n_candidates)
    else:
        logger.info("No qualified candidates to send to n8n.")

    # 4: Generate quiz for a job description and sector
    logger.info("Generating quiz for feild: %s in sector: %s", job_field, sector)
    generated_quiz = gpt_quiz(job_description, sector, job_field, data_path)
    with open("generated_quiz.json", "w", encoding="utf-8") as f:
      json.dump(generated_quiz, f, ensure_ascii=False, indent=4)
    logger.info("Quiz generated successfully.")
    print(generated_quiz)

    sample_answer = """
    from sklearn.linear_model import LinearRegression

    def train_model(X_train, y_train):
        model = LinearRegression()
        model.fit(X_train, y_train)
        return model
    """

    # 5: Evaluate applicant answers to the quiz
    logger.info("Evaluating applicant answers for sector: %s", sector)
    evaluation_report = evaluate_answer(generated_quiz, sample_answer, job_field)
    logger.info("Evaluation completed successfully.")
    logger.info("Evaluation Summary:\n%s", evaluation_report)
    print(evaluation_report)

    config = Config('.env')
    client = OpenAI(api_key=config.api_key)
    def get_gpt_answer(question):
        response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"Solve this question:\n{question}"}]
    )
        return response.choices[0].message.content
    
    # 6: Shortlist applicants based on quiz results
    shortlisted_candidates = []
    passing_score = 4.0  # معيار النجاح على مقياس 0-10
    for candidate in qualified_candidates:
        if evaluation_report["overall_score"] >= passing_score:
            shortlisted_candidates.append(candidate)
    logger.info("Shortlisted %d candidates based on quiz results.", len(shortlisted_candidates))

    # Save shortlisted candidates
    with open("shortlisted_candidates.json", "w", encoding="utf-8") as f:
        json.dump(shortlisted_candidates, f, ensure_ascii=False, indent=4)


# عدلت على الكود و هذي النسخة القديمه لو احتجتوها
#    # 1: Handling applicant CV
#    if cv_files:
#        logger.info("Extracting CVs from files: %s", cv_files)
#        extractor = CVExtractor(config)
#        cv_file = extractor.process_batch(cv_files)
#        logger.info("CVs extracted successfully")
#    else:
#        logger.warning("No CV files provided, proceeding without CV extraction.")
#        cv_file = None
#
#    # 2: Handling job description
#
#    # 3: Embbidings to get possible applicants for a job description
#    if cv_file:
#        logger.info("Matching candidates for job field: %s", job_field)
#        qualified_candidates = match_candidates(
#            cvs_data=cv_file,
#            job_description=job_description,
#            job_field=job_field,
#            output_path="qualified_candidates.json"
#        )
#        logger.info("Found %d qualified candidates", len(qualified_candidates))
#    else:
#        qualified_candidates = []
#        logger.warning("No CVs to match. Skipping candidate matching.")



if __name__ == "__main__":
    main(
        job_description="Write a function to train a simple linear regression model using scikit-learn.",
        sector="software_engineer",
        job_field="software engineering"
    )
