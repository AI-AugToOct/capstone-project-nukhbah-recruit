import json
import copy
from src.infra.gpt_client import get_gpt_client
from src.config.config import GPT_PROMPT, GPT_MODEL, GPT_TEMPERATURE
import pandas as pd


gpt_client = get_gpt_client()
def gpt_quiz(job_description: str, sector: str, job_field: str, data_path: str = None):
    formatted_prompt = None

    if job_field == "Fullstack Developer":
        formatted_prompt = copy.deepcopy(GPT_PROMPT["full_stack_developer"])
    elif job_field == "AI Engineer":
        formatted_prompt = copy.deepcopy(GPT_PROMPT["ai_engineering"])
    elif job_field == "Cyber Security":
        formatted_prompt = copy.deepcopy(GPT_PROMPT["cyber_security"])
    elif job_field == "Cloud Engineer":
        formatted_prompt = copy.deepcopy(GPT_PROMPT["cloud_engineering"])
    elif job_field == "Software Engineer":
        formatted_prompt = copy.deepcopy(GPT_PROMPT["software_engineering"])
    else:
        raise ValueError(f"Unsupported job field: {job_field}")

    data_context = ""
    if job_field == "ai engineering":
        if data_path is None:
            raise ValueError("Dataset path is required for AI Engineering quizzes")
        df = pd.read_csv(data_path)
        data_context = (
            f"Columns: {list(df.columns)}\n\n"
            f"Sample rows:\n{df.head(5).to_string(index=False)}"
        )
        formatted_prompt[1]["content"] = formatted_prompt[1]["content"].format(
            description=job_description, sector=sector, dataset=data_context
        )

    
    elif job_field == "cyber security":
        if data_path is None:
            raise ValueError("Data path is required for Cybersecurity quizzes")

        if data_path.endswith(".csv"):
            df = pd.read_csv(data_path)
            data_context = (
                f"CSV file detected.\nColumns: {list(df.columns)}\n\n"
                f"Sample rows:\n{df.head(5).to_string(index=False)}"
            )

        elif data_path.endswith(".json"):
            with open(data_path, "r") as f:
                data = json.load(f)
            data_context = (
                "JSON file detected.\nSample entries:\n"
                + json.dumps(data[:3], indent=2)
            )

        elif data_path.endswith(".log") or data_path.endswith(".txt"):
            with open(data_path, "r") as f:
                lines = f.readlines()
            data_context = (
                "Syslog file detected.\nSample log lines:\n"
                + "".join(lines[:5])
            )

        else:
            raise ValueError("Unsupported file format for Cybersecurity quizzes")

        formatted_prompt[1]["content"] = formatted_prompt[1]["content"].format(
            description=job_description, sector=sector, dataset=data_context
        )

    else:
        formatted_prompt[1]["content"] = formatted_prompt[1]["content"].format(
            description=job_description, sector=sector
        )


    response = gpt_client.chat.completions.create(
        model=GPT_MODEL,
        messages=formatted_prompt,
        max_tokens=1500,
        temperature=GPT_TEMPERATURE,
    )

    return response.choices[0].message.content.strip()
