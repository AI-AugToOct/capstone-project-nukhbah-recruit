from pathlib import Path
import json
from config import Config
from src.cv_extractor import CVExtractor
# from src.cv_extractor import extract_cvs
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

config = Config('.env')


def main(job_description: str, sector: str, job_field: str, cv_file_path: str = "src/all_cvs_database.json", data_path: str = None):
    
    cvs_data = []

    # 1: Extracting applicant CVs
    if cv_files:
        logger.info("Extracting CVs from files: %s", cv_files)

        cv_file_path = extract_cvs(cv_files)

        with open(cv_file_path, 'r', encoding='utf-8') as f:
            cvs_data = list(json.load(f).values())

        logger.info("CVs extracted successfully: %d candidates", len(cvs_data))
    else:
        logger.warning("No CV files provided, proceeding without CV extraction.")

    # 2: Matching candidates to job description
    
    qualified_candidates = []
    if cvs_data:
        qualified_candidates = match_candidates(
            cvs_data=cvs_data,
            job_description=job_description,
            job_field=job_field,
            output_path="qualified_candidates.json"
        )
        logger.info("Total qualified candidates: %d", len(qualified_candidates))
    else:
        logger.warning("No CVs available to match.")

    # 4: Generate quiz for a job description and sector
    logger.info("Generating quiz for feild: %s in sector: %s", job_field, sector)
    generated_quiz = gpt_quiz(job_description, sector, job_field, data_path)
    logger.info("Quiz generated successfully.")
    print(generated_quiz)
    # 4: Generate quiz for a job description and sector
    logger.info("Generating quiz for field: %s in sector: %s", job_field, sector)
    generated_quiz = gpt_quiz(job_description, sector, job_field, data_path)
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
    evaluation_report = evaluate_answer(generated_quiz, sample_answer, sector)
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
