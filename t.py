# Open a file (for example, 'example.txt') in read mode
from pathlib import Path

UPLOADS_DIR = Path(__file__).parent / "src" / "uploads"


data_path= UPLOADS_DIR / "data.csv"

print(data_path)
try:
    file = open(data_path, 'r')
    print("File opened successfully.")
    file.close()
except FileNotFoundError:
    print("The file does not exist.")
except IOError as e:
    print(f"An I/O error occurred: {e}")
