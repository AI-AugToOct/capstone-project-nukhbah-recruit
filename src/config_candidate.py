# src/config_candidate.py

import configparser
import os

current_path = os.getcwd()
files_and_dirs = os.listdir(os.getcwd())

config = configparser.ConfigParser()
config.read(".env")

# ✅ تحويل القيم الرقمية إلى النوع الصحيح
SIMILARITY_THRESHOLD = float(config["Settings"]["SIMILARITY_THRESHOLD"])
CHUNK_SIZE = int(config["Settings"]["CHUNK_SIZE"])
OVERLAP = int(config["Settings"]["OVERLAP"])
