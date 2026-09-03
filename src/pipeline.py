import cv2
import time

from ultralytics import YOLO
from predict_weather import load_weather_model, predict_weather
from sensor_reader import load_telemetry, sensor_confidence_at
from fusion import fuse

model = YOLO("runs/detect/nayan_sevak/weights/best.pt")
weather_model = load_weather_model()
telemetry = load_telemetry()

CLASS_NAMES = {
    0: "pothole",
    1: "Green Light",
    2: "Red Light",
    3: "Speed Limit 10",
    4: "Speed Limit 100",
    5: "Speed Limit 110",
    6: "Speed Limit 120",
    7: "Speed Limit 20",
    8: "Speed Limit 30",
    9: "Speed Limit 40",
    10: "Speed Limit 50",
    11: "Speed Limit 60",
    12: "Speed Limit 70",
    13: "Speed Limit 80",
    14: "Speed Limit 90",
    15: "Stop"
}

TIER_COLORS = {
    "CRITICAL": (0, 0, 255),
    "WARNING":  (0, 165, 255),
    "NOMINAL":  (0, 255, 0),
}

def run_pipeline(source=0, interval=6, conf=0.4, weather_check_interval=10):
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print("Could not open video source")
        return

    print(f"Pipeline started. Detecting every {interval}s. Press Q to quit.")

    last_detect_time = 0
    last_detections = []
    weather_state = "sunny"
    frame_count = 0
    start_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = time.time()
        frame_count += 1

        if current_time - last_detect_time >= interval:
            last_detect_time = current_time

            if frame_count % weather_check_interval == 0:
                weather_state = predict_weather(weather_model, frame)

            elapsed = current_time - start_time
            sensor_conf = sensor_confidence_at(telemetry, elapsed)

            results = model.track(frame, conf=conf, verbose=False, device="mps", persist=True)
            last_detections = []

            for result in results:
                for box in result.boxes:
                    cls_id = int(box.cls)
                    label = CLASS_NAMES.get(cls_id, "unknown")
                    confidence = float(box.conf)
                    track_id = int(box.id) if box.id is not None else -1
                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    fused_conf, tier = fuse(track_id, confidence, sensor_conf, weather_state)

                    last_detections.append({
                        "label": label,
                        "conf": confidence,
                        "fused": fused_conf,
                        "tier": tier,
                        "bbox": (x1, y1, x2, y2)
                    })

            if last_detections:
                print(f"\n[{time.strftime('%H:%M:%S')}] Weather: {weather_state} | Detections:")
                for det in last_detections:
                    print(f"  {det['label']} raw={det['conf']:.0%} fused={det['fused']:.0%} [{det['tier']}]")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] Weather: {weather_state} | No detections")

        display = frame.copy()
        for det in last_detections:
            x1, y1, x2, y2 = det["bbox"]
            color = TIER_COLORS[det["tier"]]
            cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
            cv2.putText(display, f"{det['label']} {det['tier']} {det['fused']:.0%}",
                        (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.putText(display, f"Weather: {weather_state}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        next_detect = max(0, interval - (current_time - last_detect_time))
        cv2.putText(display, f"Next scan in: {next_detect:.1f}s",
                    (10, display.shape[0] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        cv2.imshow("Car Vigilanty Assistant", display)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Pipeline stopped.")

if __name__ == "__main__":
    #run_pipeline(source=0, interval=0.1, conf=0.4)
    run_pipeline(source="data/road_dataset/sample_video.mp4", interval=0.1, conf=0.4)