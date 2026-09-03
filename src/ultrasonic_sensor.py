import numpy as np
import pandas as pd
from scipy.ndimage import median_filter

SAMPLE_RATE = 20
MEDIAN_WINDOW = 5
EMA_ALPHA = 0.3
PROXIMITY_THRESHOLD = 150
CRITICAL_THRESHOLD = 50
HISTORY_SIZE = SAMPLE_RATE

def ema_filter(data, alpha):
    smoothed = np.zeros(len(data))
    smoothed[0] = data[0]
    for i in range(1, len(data)):
        smoothed[i] = alpha * data[i] + (1 - alpha) * smoothed[i - 1]
    return smoothed

def calculate_ultrasonic_score(distance, closing_rate):
    if distance >= PROXIMITY_THRESHOLD:
        distance_score = 0.0
    elif distance <= CRITICAL_THRESHOLD:
        distance_score = 1.0
    else:
        distance_score = (PROXIMITY_THRESHOLD - distance) / (PROXIMITY_THRESHOLD - CRITICAL_THRESHOLD)

    closing_score = np.clip(closing_rate / 100.0, 0.0, 1.0)
    ultrasonic_score = 0.7 * distance_score + 0.3 * closing_score

    return float(np.clip(ultrasonic_score, 0.0, 1.0))

def process_ultrasonic_file(filepath):
    df = pd.read_csv(filepath)

    if "distance" not in df.columns:
        raise ValueError(f"Missing column 'distance' in {filepath}")

    distance = df["distance"].values.astype(float)

    distance = median_filter(distance, size=MEDIAN_WINDOW)
    distance = ema_filter(distance, EMA_ALPHA)

    samples = []

    for i in range(1, len(distance)):
        current_distance = distance[i]
        delta_distance = current_distance - distance[i - 1]
        closing_rate = -delta_distance * SAMPLE_RATE

        start = max(0, i - HISTORY_SIZE + 1)
        min_distance = np.min(distance[start:i + 1])
        ultrasonic_score = calculate_ultrasonic_score(current_distance, closing_rate)

        if current_distance <= CRITICAL_THRESHOLD:
            status = 2
        elif current_distance <= PROXIMITY_THRESHOLD:
            status = 1
        else:
            status = 0

        samples.append([
            current_distance,
            closing_rate,
            min_distance,
            ultrasonic_score,
            status
        ])

    return np.array(samples)

def main():
    filepath = "data/sensor_dataset/ultrasonic_data.csv"
    data = process_ultrasonic_file(filepath)

    if len(data) == 0:
        print("No data found!")
        return

    print(f"Total samples: {len(data)}")
    print("Distance | Closing Rate | Min Distance | Score | Status")

    for sample in data:
        distance, closing_rate, min_distance, ultrasonic_score, status = sample

        if status == 0:
            label = "Safe"
        elif status == 1:
            label = "Obstacle"
        else:
            label = "Critical"

        print(f"{distance:8.2f} | {closing_rate:12.2f} | {min_distance:12.2f} | {ultrasonic_score:5.3f} | {label}")

if __name__ == "__main__":
    main()