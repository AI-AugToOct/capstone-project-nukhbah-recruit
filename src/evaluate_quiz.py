import json
import kagglehub
import pandas as pd
from pathlib import Path
from src.infra.gpt_client import get_gpt_client
from src.evaluation_criteria import EVALUATION_CRITERIA
from src.evaluation_config import EVALUATION_PROMPT

gpt_client = get_gpt_client()


def evaluate_answer(question: str, answer: str, role: str):
    """
    Evaluates a candidate's quiz answer based on job-specific weighted criteria.
    Uses a Chain-of-Thought (CoT) reasoning approach internally.
    """

    criteria_obj = EVALUATION_CRITERIA.get(role, {})
    weights = criteria_obj.get("weights", {})
    descriptions = criteria_obj.get("descriptions", {})

    criteria_text = "\n".join([
        f"- {name} ({weights[name]*100:.0f}%): {descriptions[name]}"
        for name in weights
    ])

    prompt = [
        {"role": "system", "content": EVALUATION_PROMPT[0]["content"]},
        {"role": "user", "content": EVALUATION_PROMPT[1]["content"].format(
            role=role,
            question=question,
            answer=answer,
            criteria=criteria_text
        )}
    ]

    response = gpt_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=prompt,
        max_tokens=1200,
        temperature=0.3
    )

    evaluation_text = response.choices[0].message.content.strip()

    try:
        evaluation_json = json.loads(evaluation_text)
    except json.JSONDecodeError:
        evaluation_json = parse_evaluation_text(evaluation_text)

    return evaluation_json


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
                    scores[criterion_name] = {"score": float(score_part), "comment": ""}
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


def evaluate_dataset_with_judge(role="Software Engineer"):
    """
    Uses the LLM-as-a-Judge system to evaluate all answers 
    in the Python MCQ dataset from Kaggle.
    """
    print("Downloading dataset from Kaggle...")
    path = kagglehub.dataset_download("kusalmadurayapa/python-mcq")

    dataset_dir = Path(path)
    csv_file = list(dataset_dir.glob("*.csv"))[0]
    df = pd.read_csv(csv_file)
    print(f"Loaded dataset with {len(df)} records.")

    results = []

    for i, row in df.iterrows():
        question = str(row.get("question", ""))
        answer = str(row.get("correct_answer", ""))

        print(f"\nEvaluating Q{i+1}/{len(df)}: {question[:80]}...")

        try:
            evaluation = evaluate_answer(question, answer, role)
        except Exception as e:
            print(f"Error evaluating Q{i+1}: {e}")
            evaluation = {"error": str(e)}

        results.append({
            "question": question,
            "answer": answer,
            "evaluation": evaluation,
            "difficulty": row.get("difficulty", "N/A"),
            "category": row.get("category", "N/A")
        })

    df_results = pd.DataFrame(results)
    df_results.to_json("llm_judge_evaluation_results.json", indent=2, force_ascii=False)

    print("\nEvaluation complete.")
    print("Results saved to llm_judge_evaluation_results.json")

    valid_scores = [
        r["evaluation"].get("overall_score")
        for _, r in df_results.iterrows()
        if isinstance(r["evaluation"], dict) and "overall_score" in r["evaluation"]
    ]
    if valid_scores:
        avg_score = sum(valid_scores) / len(valid_scores)
        print(f"Average Overall Score: {avg_score:.2f}/10")


if __name__ == "__main__":
    # Single question test
    question = "Write a function to train a simple linear regression model using scikit-learn."
    answer = """
from sklearn.linear_model import LinearRegression

def train_model(X_train, y_train):
    model = LinearRegression()
    model.fit(X_train, y_train)
    return model
"""
    role = "Software Engineer"

    print("\nSingle Evaluation Test:")
    result = evaluate_answer(question, answer, role)
    print(json.dumps(result, indent=2))

    # Full dataset evaluation
    print("\nRunning dataset-wide evaluation...")
    evaluate_dataset_with_judge(role="Software Engineer")
