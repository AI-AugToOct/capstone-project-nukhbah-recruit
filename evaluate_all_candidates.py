import json
import logging
from pathlib import Path
from src.evaluate_quiz import evaluate_answer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def evaluate_all_candidates_from_json(
    master_file: str = "all_candidates_answers.json",
    output_file: str = "evaluation_results.json"
):
    """
    Evaluate all candidates from the master JSON file.
    Reads all_candidates_answers.json and evaluates each candidate's answer.
    """
    
    # Check if master file exists
    if not Path(master_file).exists():
        logger.error(f"Master file not found: {master_file}")
        return None
    
    # Load master JSON
    with open(master_file, 'r', encoding='utf-8') as f:
        master_data = json.load(f)
    
    logger.info(f"Loaded master file with {len(master_data)} job positions")
    
    # Store evaluation results
    evaluation_results = {}
    
    # Evaluate each job position
    for job_field, job_data in master_data.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"Evaluating {job_field.upper()} candidates...")
        logger.info(f"{'='*60}")
        
        question = job_data["question"]
        candidates = job_data["candidates"]
        
        evaluation_results[job_field] = {
            "job_description": job_data["job_description"],
            "question": question,
            "candidate_evaluations": {}
        }
        
        # Evaluate each candidate
        for candidate_id, candidate_info in candidates.items():
            candidate_name = candidate_info["name"]
            answer = candidate_info["answer"]
            
            logger.info(f"\nEvaluating {candidate_name} ({candidate_id})...")
            
            try:
                # Call the evaluate_answer function
                evaluation = evaluate_answer(
                    question=question,
                    answer=answer,
                    role=job_field  # Use job_field as role
                )
                
                # Store evaluation result
                evaluation_results[job_field]["candidate_evaluations"][candidate_id] = {
                    "name": candidate_name,
                    "file": candidate_info["file"],
                    "evaluation": evaluation,
                    "overall_score": evaluation.get("overall_score", 0),
                    "recommendation": evaluation.get("recommendation", "FAIL")
                }
                
                logger.info(f"✓ Score: {evaluation.get('overall_score', 0)}/10 - {evaluation.get('recommendation', 'N/A')}")
                
                # Mark as evaluated in master file
                master_data[job_field]["candidates"][candidate_id]["evaluated"] = True
                
            except Exception as e:
                logger.error(f"✗ Error evaluating {candidate_name}: {e}")
                evaluation_results[job_field]["candidate_evaluations"][candidate_id] = {
                    "name": candidate_name,
                    "file": candidate_info["file"],
                    "evaluation": {"error": str(e)},
                    "overall_score": 0,
                    "recommendation": "ERROR"
                }
        
        # Calculate statistics for this job
        scores = [
            c["overall_score"] 
            for c in evaluation_results[job_field]["candidate_evaluations"].values()
            if c["overall_score"] > 0
        ]
        
        if scores:
            evaluation_results[job_field]["statistics"] = {
                "total_candidates": len(candidates),
                "average_score": sum(scores) / len(scores),
                "highest_score": max(scores),
                "lowest_score": min(scores),
                "passed": sum(1 for s in scores if s >= 7.0),
                "failed": sum(1 for s in scores if s < 7.0)
            }
    
    # Save evaluation results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(evaluation_results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"✓ Evaluation complete! Results saved to {output_file}")
    logger.info(f"{'='*60}")
    
    # Update master file with evaluated status
    with open(master_file, 'w', encoding='utf-8') as f:
        json.dump(master_data, f, indent=2, ensure_ascii=False)
    
    return evaluation_results


def display_evaluation_summary(results_file: str = "evaluation_results.json"):
    """Display a summary of all evaluation results."""
    
    if not Path(results_file).exists():
        print(f"No results file found: {results_file}")
        return
    
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    print("\n" + "="*70)
    print("EVALUATION SUMMARY")
    print("="*70)
    
    for job_field, job_results in results.items():
        print(f"\n📋 {job_field.upper().replace('_', ' ')}")
        
        if "statistics" in job_results:
            stats = job_results["statistics"]
            print(f"   Total Candidates: {stats['total_candidates']}")
            print(f"   Average Score: {stats['average_score']:.2f}/10")
            print(f"   Passed: {stats['passed']} | Failed: {stats['failed']}")
            print(f"   Highest: {stats['highest_score']:.2f} | Lowest: {stats['lowest_score']:.2f}")
        
        print(f"\n   Top Candidates:")
        
        # Sort candidates by score
        candidates = job_results["candidate_evaluations"]
        sorted_candidates = sorted(
            candidates.items(),
            key=lambda x: x[1]["overall_score"],
            reverse=True
        )
        
        for i, (candidate_id, data) in enumerate(sorted_candidates[:5], 1):
            score = data["overall_score"]
            rec = data["recommendation"]
            print(f"   {i}. {data['name']}: {score}/10 ({rec})")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    print("="*70)
    print("EVALUATING ALL CANDIDATES")
    print("="*70)
    
    # Evaluate all candidates
    results = evaluate_all_candidates_from_json(
        master_file="all_candidates_answers.json",
        output_file="evaluation_results.json"
    )
    
    if results:
        # Display summary
        display_evaluation_summary("evaluation_results.json")