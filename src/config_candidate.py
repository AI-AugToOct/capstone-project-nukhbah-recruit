# src/config_candidate.py

import configparser
import os


# base_dir = os.path.dirname(os.path.abspath(__file__))
# env_path = os.path.join(base_dir, ".env")

# config = configparser.ConfigParser()
# config.read(env_path)

# if "Settings" not in config:
#     raise ValueError("Section [Settings] not found in .env")

# candidate matching parameters
# SIMILARITY_THRESHOLD = float(config["Settings"].get("SIMILARITY_THRESHOLD", 0.75))
# CHUNK_SIZE = int(config["Settings"].get("CHUNK_SIZE", 60))
# OVERLAP = int(config["Settings"].get("OVERLAP", 20))
current_path = os.getcwd()
files_and_dirs = os.listdir(os.getcwd())

config = configparser.ConfigParser()
config.read(".env")

SIMILARITY_THRESHOLD= config["Settings"]["SIMILARITY_THRESHOLD"]
CHUNK_SIZE = config["Settings"]["CHUNK_SIZE"]
OVERLAP = config["Settings"]["OVERLAP"]

