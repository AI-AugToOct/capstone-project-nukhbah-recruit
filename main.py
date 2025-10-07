from pathlib import Path
import json
import logging
from config import Config
from src.cv_extractor import CVExtractor
from src.generate_gpt_quiz import gpt_quiz
from src.job_desc_samples import (
    ai_description,
    cyber_security_description,
    software_engineering_description,
    cloud_engineering_description,
)
from src.candidate_matching import match_candidates
from src.evaluate_quiz import evaluate_answer
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = Config(".env")
client = OpenAI(api_key=config.api_key)


# GPT Answer Generator
def get_gpt_answer(question):
    """Ask GPT to solve a quiz question and print its answer."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"Solve this question:\n{question}"}],
        )

        answer = response.choices[0].message.content.strip()

        print("\n--- GPT Generated Answer ---")
        print(answer)
        print("---------------------------------\n")

        return answer

    except Exception as e:
        logger.error(f"Error generating GPT answer: {e}")
        return None


# Main Pipeline
def main(job_description: str, sector: str, job_field: str, cv_files: list = None, data_path: str = None):
    cvs_data = []

    # Step 1: Extract CVs
    if cv_files:
        logger.info("Extracting CVs from files: %s", cv_files)
        cv_file_path = extract_cvs(cv_files)
        with open(cv_file_path, "r", encoding="utf-8") as f:
            cvs_data = list(json.load(f).values())
        logger.info("CVs extracted successfully: %d candidates", len(cvs_data))
    else:
        logger.warning("No CV files provided, proceeding without CV extraction.")

    # Step 2: Match Candidates
    qualified_candidates = []
    if cvs_data:
        logger.info("Matching candidates for job field: %s", job_field)
        qualified_candidates = match_candidates(
            cvs_data=cvs_data,
            job_description=job_description,
            job_field=job_field,
            output_path="qualified_candidates.json",
        )
        logger.info("Found %d qualified candidates", len(qualified_candidates))
    else:
        logger.warning("No CVs to match. Skipping candidate matching.")

    # Step 3: Generate Quiz
    logger.info("Generating quiz for field: %s in sector: %s", job_field, sector)
    generated_quiz = gpt_quiz(job_description, sector, job_field, data_path)
    logger.info("Quiz generated successfully.")
    print(generated_quiz)

    # Step 4: Generate GPT’s Answer
    logger.info("Generating GPT’s own answer to the quiz...")
    if isinstance(generated_quiz, list):
        for q in generated_quiz:
            question_text = q.get("question") if isinstance(q, dict) else str(q)
            get_gpt_answer(question_text)
    else:
        get_gpt_answer(str(generated_quiz))

    # Step 5: Evaluate Sample Answer
    sample_answer = """
from sklearn.linear_model import LinearRegression

def train_model(X_train, y_train):
    model = LinearRegression()
    model.fit(X_train, y_train)
    return model
"""
    logger.info("Evaluating applicant answers for sector: %s", sector)
    evaluation_report = evaluate_answer(generated_quiz, sample_answer, sector)
    logger.info("Evaluation completed successfully.")
    print(evaluation_report)


# Entry Point
if __name__ == "__main__":
    main(
        job_description="Write a function to train a simple linear regression model using scikit-learn.",
        sector="software_engineer",
        job_field="software engineering",
    )