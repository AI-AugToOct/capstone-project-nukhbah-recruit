from pathlib import Path
import json
from config import Config
from cv_extractor import CVExtractor
from src.generate_gpt_quiz import gpt_quiz
from src.job_desc_samples import ai_description, cyber_security_description, software_engineering_description, cloud_engineering_description
import logging
from src.candidate_matching import match_candidates
from src.config_candidate import SIMILARITY_THRESHOLD, CHUNK_SIZE, OVERLAP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = Config('.env')

def extract_cvs(cv_files: list) -> str:
    extractor = CVExtractor(config)
    
    valid_files = [f for f in cv_files if Path(f).exists()]
    
    if not valid_files:
        logger.error("No valid CV files found")
        return None
    
    extracted_cvs = extractor.process_batch(valid_files)
    
    cv_data_dict = {cv.get('filename'): cv for cv in extracted_cvs}
    
    output_file = config.output_dir / "all_extracted_cvs.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cv_data_dict, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Extracted {len(cv_data_dict)} CVs: {output_file}")
    
    return str(output_file)


def main(job_description: str, sector: str, job_field: str, cv_files: list = None, data_path: str = None):

    # 1: Handling applicant CV
    if cv_files:
        cv_file = extract_cvs(cv_files)
    else:
        cv_file = None

    # 2: Handling job description

    # 3: Embbidings to get possible applicants for a job description
    logger.info("Matching candidates for job field: %s", job_field)
    qualified_candidates = match_candidates(cv_file, job_description, job_field, "qualified_candidates.json")
    logger.info("Found %d qualified candidates", len(qualified_candidates))
    # اسم الملف اللى فيه المترشحين qualified_candidates.json

    # 4: Generate quiz for a job description and sector
    logger.info("Generating quiz for feild: %s in sector: %s", job_field, sector)
    generated_quiz = gpt_quiz(job_description, sector, job_field, data_path)
    logger.info("Quiz generated successfully.")

    # 5: Evaluate applicant answers to the quiz

    # 6: Shortlist applicants based on quiz results

    return