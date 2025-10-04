from src.generate_gpt_quiz import gpt_quiz
from src.job_desc_samples import ai_description, cyber_security_description, software_engineering_description, cloud_engineering_description
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



def main(job_description: str, sector: str, job_field: str, data_path: str = None):

# 1: Handling applicant CV 

# 2: Handling job description

# 3: Embbidings to get possible applicants for a job description

# 4: Generate quiz for a job description and sector 
    logger.info("Generating quiz for feild: %s in sector: %s", job_field, sector)
    generated_quiz = gpt_quiz(job_description, sector, job_field, data_path)
    logger.info("Quiz generated successfully.")
# 5: Evaluate applicant answers to the quiz

# 6: Shortlist applicants based on quiz results 

    return