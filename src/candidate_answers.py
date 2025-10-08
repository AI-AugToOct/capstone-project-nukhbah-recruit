
import json
from pathlib import Path

def store_candidate_answer(candidate_id: str, question: str, answer: str, 
                          output_file: str = "candidate_answers.json"):
    """Store a candidate's answer to a quiz question."""
    
 
    answers_file = Path(output_file)
    if answers_file.exists():
        with open(answers_file, 'r') as f:
            all_answers = json.load(f)
    else:
        all_answers = {}
    
    # Store answer
    if candidate_id not in all_answers:
        all_answers[candidate_id] = []
    
    all_answers[candidate_id].append({
        "question": question,
        "answer": answer,
        "timestamp": str(pd.Timestamp.now())
    })
    
   
    with open(answers_file, 'w') as f:
        json.dump(all_answers, f, indent=2)
    
    return output_file


