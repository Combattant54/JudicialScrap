import json

JSON_DATA_PATH = "data.json"

DATA = None

with open(JSON_DATA_PATH, "r") as f:
    DATA = json.loads(f.read())

with open(JSON_DATA_PATH, "w") as f:
    DATA = json.dump(DATA, f, indent="  ")