
# Handles evaluation of candidate submissions using the
# LLM-as-a-Judge approach with role-based criteria.

import json
from gpt_client import get_gpt_client
from EvaluationCriteria import EvaluationCriteria
from evaluation_config import EVALUATION_PROMPT


# Initialize GPT client

gpt_client = get_gpt_client()


#
# Evaluate one submission

def evaluate_answer(question: str, answer: str, role: str):
    """
    Evaluates a candidate's quiz answer based on job-specific weighted criteria.
    Uses a Chain-of-Thought (CoT) reasoning approach internally.
    """

    # --- Load criteria for this role
    criteria_obj = EvaluationCriteria(role)
    weights = criteria_obj.get_weights()
    descriptions = criteria_obj.get_descriptions()

    # --- Build criteria text for the LLM
    criteria_text = "\n".join([
        f"- {name} ({weights[name]*100:.0f}%): {descriptions[name]}"
        for name in weights
    ])

    # --- Format the evaluation prompt
    prompt = [
        {
            "role": "system",
            "content": EVALUATION_PROMPT[0]["content"]
        },
        {
            "role": "user",
            "content": EVALUATION_PROMPT[1]["content"].format(
                role=role,
                question=question,
                answer=answer,
                criteria=criteria_text
            )
        }
    ]

    # --- Query the LLM
    response = gpt_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=prompt,
        max_tokens=1200,
        temperature=0.3  # Low temperature = consistent scoring
    )

    evaluation_text = response.choices[0].message.content.strip()

    # --- Try JSON parsing
    try:
        evaluation_json = json.loads(evaluation_text)
    except json.JSONDecodeError:
        # fallback parser for plain-text output
        evaluation_json = parse_evaluation_text(evaluation_text)

    return evaluation_json


# Fallback parser (for non-JSON LLM output)

def parse_evaluation_text(evaluation_text: str):
    """
    Parses text output if the model fails to return strict JSON.
    Expected lines:
      Criterion: X/10
      Overall Score: Y/10
      Recommendation: PASS/FAIL
    """
    lines = evaluation_text.strip().split('\n')
    scores = {}
    overall_score = None
    recommendation = None

    for line in lines:
        if '/10' in line and 'Overall' not in line:
            parts = line.split(':')
            if len(parts) >= 2:
                criterion_name = parts[0].strip().replace("-", "")
                score_part = parts[1].split('/10')[0].strip()
                try:
                    scores[criterion_name] = {
                        "score": float(score_part),
                        "comment": ""
                    }
                except ValueError:
                    continue
        elif 'Overall Score:' in line:
            try:
                overall_score = float(line.split(':')[1].split('/10')[0].strip())
            except ValueError:
                pass
        elif 'Recommendation:' in line:
            if 'PASS' in line.upper():
                recommendation = 'PASS'
            elif 'FAIL' in line.upper():
                recommendation = 'FAIL'

    if overall_score is None and scores:
        avg = sum(v["score"] for v in scores.values()) / len(scores)
        overall_score = round(avg, 1)

    return {
        "criteria_scores": scores,
        "overall_score": overall_score,
        "recommendation": recommendation,
        "summary": evaluation_text
    }



# Example standalone test

if __name__ == "__main__":
    question = "Write a function to train a simple linear regression model using scikit-learn."
    answer = """
from sklearn.linear_model import LinearRegression

def train_model(X_train, y_train):
    model = LinearRegression()
    model.fit(X_train, y_train)
    return model
"""
    role = "AI Engineer"

    result = evaluate_answer(question, answer, role)
    print(json.dumps(result, indent=2))
