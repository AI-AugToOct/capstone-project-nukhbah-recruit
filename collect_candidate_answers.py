import json
import logging
from pathlib import Path
from typing import Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def read_answer_file(file_path: str) -> str:
    """
    Read candidate answer from a file.
    Supports: .txt, .py, .md, .json
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    logger.info(f"Read {len(content)} characters from {file_path.name}")
    return content


def collect_answers_for_job(
    job_field: str,
    job_description: str,
    question: str,
    answers_dir: str,
    output_file: str = "all_candidates_answers.json"
) -> Dict:
    """
    Collect candidate answers for a specific job and add to master JSON.
    
    Args:
        job_field: e.g., "software_engineer", "ai_engineer"
        job_description: Full job description
        question: The quiz question for this job
        answers_dir: Directory containing candidate answer files
        output_file: Master JSON file (default: all_candidates_answers.json)
    """
    answers_path = Path(answers_dir)
    
    if not answers_path.exists():
        raise FileNotFoundError(f"Directory not found: {answers_dir}")
    
    # Get all answer files
    answer_files = []
    for ext in ['*.txt', '*.py', '*.md', '*.json']:
        answer_files.extend(answers_path.glob(ext))
    
    if not answer_files:
        logger.warning(f"No answer files found in {answers_dir}")
        return {}
    
    logger.info(f"Found {len(answer_files)} answer files for {job_field}")
    
    # Load existing master JSON or create new
    output_path = Path(output_file)
    if output_path.exists():
        with open(output_file, 'r', encoding='utf-8') as f:
            master_data = json.load(f)
    else:
        master_data = {}
    
    # Initialize job entry if not exists
    if job_field not in master_data:
        master_data[job_field] = {
            "job_description": job_description,
            "question": question,
            "candidates": {}
        }
    
    # Collect candidate answers
    candidates_collected = 0
    
    for file_path in sorted(answer_files):
        filename = file_path.stem
        parts = filename.split('_')
        
        # Parse filename: candidate_001_john_doe
        if len(parts) >= 3 and parts[0] == 'candidate':
            candidate_id = f"candidate_{parts[1]}"
            candidate_name = ' '.join(parts[2:]).replace('_', ' ').title()
        else:
            candidate_id = filename
            candidate_name = filename.replace('_', ' ').title()
        
        # Read answer
        try:
            answer_content = read_answer_file(file_path)
            
            master_data[job_field]["candidates"][candidate_id] = {
                "name": candidate_name,
                "file": str(file_path.name),
                "answer": answer_content,
                "evaluated": False
            }
            
            logger.info(f"✓ Added {candidate_name} ({candidate_id}) to {job_field}")
            candidates_collected += 1
            
        except Exception as e:
            logger.error(f"✗ Error reading {file_path.name}: {e}")
            continue
    
    # Save master JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(master_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\n✓ Saved {candidates_collected} candidates for {job_field}")
    logger.info(f"✓ Master file: {output_file}")
    
    return master_data


def display_all_jobs(master_file: str = "all_candidates_answers.json"):
    """Display summary of all jobs and candidates in master JSON."""
    if not Path(master_file).exists():
        print(f"No master file found: {master_file}")
        return
    
    with open(master_file, 'r') as f:
        master_data = json.load(f)
    
    print("\n" + "="*70)
    print("ALL JOBS & CANDIDATES")
    print("="*70)
    
    total_candidates = 0
    
    for job_field, job_data in master_data.items():
        num_candidates = len(job_data["candidates"])
        total_candidates += num_candidates
        
        print(f"\n{job_field.upper().replace('_', ' ')}")
        print(f"   Question: {job_data['question'][:80]}...")
        print(f"   Candidates: {num_candidates}")
        
        for candidate_id, candidate_info in job_data["candidates"].items():
            status = "✓ Evaluated" if candidate_info.get("evaluated") else " Pending"
            print(f"      - {candidate_info['name']} ({candidate_id}) {status}")
    
    print(f"\n{'='*70}")
    print(f"Total Jobs: {len(master_data)}")
    print(f"Total Candidates: {total_candidates}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    print("="*70)
    print("COLLECTING CANDIDATE ANSWERS - MASTER JSON SYSTEM")
    print("="*70)
    
    # Example: Collect for Software Engineer position
    try:
        print("\n1️ Collecting Software Engineer candidates...")
        collect_answers_for_job(
            job_field="software_engineer",
            job_description="Senior Software Engineer position requiring strong algorithmic skills",
            question="Write a function to train a simple linear regression model using scikit-learn.",
            answers_dir="candidate_answers_input/software_engineer",
            output_file="all_candidates_answers.json"
        )
    except FileNotFoundError as e:
        print(f"    Skipped: {e}")
    
    # Example: Collect for AI Engineer position
    try:
        print("\n2️ Collecting AI Engineer candidates...")
        collect_answers_for_job(
            job_field="ai_engineer",
            job_description="AI Engineer with deep learning expertise",
            question="Build a CNN model for image classification using TensorFlow.",
            answers_dir="candidate_answers_input/ai_engineer",
            output_file="all_candidates_answers.json"
        )
    except FileNotFoundError as e:
        print(f"   Skipped: {e}")
    
    # Display summary
    print("\n" + "="*70)
    display_all_jobs("all_candidates_answers.json")