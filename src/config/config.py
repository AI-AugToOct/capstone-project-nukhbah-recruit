import configparser
import json
import os

current_path = os.getcwd()
files_and_dirs = os.listdir(os.getcwd())

config = configparser.ConfigParser()
config.read(".env")

GPT_API_KEY= config["OpenAI"]["API_KEY"]
GPT_MODEL = config["Settings"]["GPT_MODEL"]
GPT_TEMPERATURE = float(config["Settings"]["GPT_TEMPERATURE"])

with open(config["Prompt"]["GPT_PROMPT"], "r") as f:
    GPT_PROMPT = json.load(f)
    
   
