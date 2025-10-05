# src/config_candidate.py

import configparser
import os


current_path = os.getcwd()
files_and_dirs = os.listdir(os.getcwd())

config = configparser.ConfigParser()
config.read(".env")

SIMILARITY_THRESHOLD= config["Settings"]["SIMILARITY_THRESHOLD"]
CHUNK_SIZE = config["Settings"]["CHUNK_SIZE"]
OVERLAP = config["Settings"]["OVERLAP"]

