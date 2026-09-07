import time
import cv2
import numpy as np
import pandas as pd

from detect import model as yolo_model, CONF_THRESHOLD, HAZARD_CLASSES
from predict_weather import load_weather_model, predict_weather_with_confidence
from vibration_sensor import (
    predict_vibration_probability,
    bandpass_filter,
    LOW_CUTOFF,
    HIGH_CUTOFF,
    SAMPLE_RATE as VIB_SAMPLE_RATE,
    WINDOW_SIZE as VIB_WINDOW_SIZE,
)
from ultrasonic_sensor import calculate_ultrasonic_score, SAMPLE_RATE as US_SAMPLE_RATE
from fusion import fusion_engine

WEATHER_CHECK_INTERVAL = 10   # frames between weather re-checks (MobileNet is heavier than a threshold check)
DETECT_INTERVAL = 0.1         # seconds between fusion ticks

VIBRATION_CSV = "data/vibration_log.csv"
ULTRASONIC_CSV = "ultrasonic_data.csv"

TIER_COLORS = {
    "CRITICAL": (0, 0, 255),
    "WARNING":  (0, 165, 255),
    "NOMINAL":  (0, 255, 0),
}


def get_camera_confidence(frame, conf):
    """Run YOLO on one frame, return the highest hazard-class confidence."""
    results = yolo_model.predict(source=frame, conf=conf, verbose=False)
    camera_confidence = 0.0
    for result in results:
        if result.boxes is None:
            continue
        for box in result.boxes:
            class_id = int(box.cls[0])
            class_name = yolo_model.names[class_id]
            if class_name in HAZARD_CLASSES:
                camera_confidence = max(camera_confidence, float(box.conf[0]))
    return camera_confidence


def get_vibration_confidence(vibration_csv, row_idx):
    """
    Read the most recent VIB_WINDOW_SIZE rows appended to the vibration log,
    filter them, and score with the trained RandomForest classifier.
    Returns (probability, new_row_idx).
    """
    df = pd.read_csv(vibration_csv)
    if len(df) < VIB_WINDOW_SIZE:
        return 0.0, row_idx

    end = len(df)
    start = end - VIB_WINDOW_SIZE
    window = df.iloc[start:end][["ax", "ay", "az"]].to_numpy(dtype=float)

    ax, ay, az = window[:, 0], window[:, 1], window[:, 2]
    magnitude = np.sqrt(ax ** 2 + ay ** 2 + az ** 2)
    magnitude = magnitude - np.mean(magnitude)
    filtered = bandpass_filter(magnitude, LOW_CUTOFF, HIGH_CUTOFF, VIB_SAMPLE_RATE)

    probability = predict_vibration_probability(filtered)
    return probability, end


def get_ultrasonic_confidence(ultrasonic_csv, row_idx):
    """
    Read the latest row appended to the ultrasonic log, derive closing rate
    from the previous row, and score it. Returns (score, new_row_idx).
    """
    df = pd.read_csv(ultrasonic_csv)
    if len(df) == 0:
        return 0.0, row_idx

    current_idx = len(df) - 1
    prev_idx = max(0, current_idx - 1)
    distance = float(df.iloc[current_idx]["distance"])
    prev_distance = float(df.iloc[prev_idx]["distance"])
    closing_rate = -(distance - prev_distance) * US_SAMPLE_RATE

    score = calculate_ultrasonic_score(distance, closing_rate)
    return score, current_idx


def run_pipeline(source=0, interval=DETECT_INTERVAL, conf=CONF_THRESHOLD,
                  weather_check_interval=WEATHER_CHECK_INTERVAL,
                  vibration_csv=VIBRATION_CSV, ultrasonic_csv=ULTRASONIC_CSV):
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print("Could not open video source")
        return

    load_weather_model()

    print(f"Pipeline started. Fusing every {interval}s. Press Q to quit.")

    last_tick = 0
    weather_state, visibility_score = "sunny", 1.0
    frame_count = 0
    vib_row_idx, us_row_idx = 0, 0
    last_result = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        now = time.time()
        frame_count += 1

        if now - last_tick >= interval:
            last_tick = now

            camera_confidence = get_camera_confidence(frame, conf)

            if frame_count % weather_check_interval == 0:
                weather_state, _, visibility_score = predict_weather_with_confidence(frame)

            vibration_confidence, vib_row_idx = get_vibration_confidence(vibration_csv, vib_row_idx)
            ultrasonic_confidence, us_row_idx = get_ultrasonic_confidence(ultrasonic_csv, us_row_idx)

            fused = fusion_engine(
                camera_confidence=camera_confidence,
                vibration_class_prob=vibration_confidence,
                ultrasonic_score=ultrasonic_confidence,
                visibility_score=visibility_score,
            )
            last_result = fused

            print(f"[{time.strftime('%H:%M:%S')}] weather={weather_state} "
                  f"cam={camera_confidence:.2f} vib={vibration_confidence:.2f} "
                  f"us={ultrasonic_confidence:.2f} -> "
                  f"combined={fused['combined_confidence']:.2f} [{fused['tier']}]")

        display = frame.copy()
        if last_result:
            color = TIER_COLORS[last_result["tier"]]
            cv2.putText(display, f"{last_result['tier']} {last_result['combined_confidence']:.0%}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(display, f"Weather: {weather_state}",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        cv2.imshow("Car Vigilanty Assistant", display)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Pipeline stopped.")

if __name__ == "__main__":
    #run_pipeline(source=0, interval=0.1, conf=0.4)
    run_pipeline(source="data/road_dataset/sample_video.mp4", interval=0.1, conf=0.4)