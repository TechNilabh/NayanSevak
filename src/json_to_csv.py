import json, csv
import os

DATA_DIR = "data/sensor_dataset"

records = []
with open(os.path.join(DATA_DIR, "sensor_data.json")) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue

with open(os.path.join(DATA_DIR, "vibration_data.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["ax", "ay", "az", "label"])
    w.writeheader()
    for r in records:
        w.writerow({k: r[k] for k in ["ax", "ay", "az", "label"]})

with open(os.path.join(DATA_DIR, "ultrasonic_data.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["distance"])
    w.writeheader()
    for r in records:
        w.writerow({"distance": r["distance"]})