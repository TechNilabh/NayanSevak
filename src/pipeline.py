import cv2
import time
from ultralytics import YOLO

model = YOLO("runs/detect/car_vigilanty_model/weights/best.pt")

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

ALERT_COLORS = {
    "pothole":      (0, 0, 255),
    "Red Light":    (0, 0, 255),
    "Stop":         (0, 0, 255),
    "Green Light":  (0, 255, 0),
}

def get_color(label):
    for key in ALERT_COLORS:
        if key in label:
            return ALERT_COLORS[key]
    return (0, 165, 255)

def run_pipeline(source=0, interval=6, conf=0.4):
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print("Could not open video source")
        return

    print(f"Pipeline started. Detecting every {interval}s. Press Q to quit.")

    last_detect_time = 0
    last_frame = None
    last_detections = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = time.time()

        if current_time - last_detect_time >= interval:
            last_detect_time = current_time
            results = model.predict(frame, conf=conf, verbose=False, device="mps")        # mps for macOS with M chip
            last_detections = []

            for result in results:
                for box in result.boxes:
                    cls_id = int(box.cls)
                    label = CLASS_NAMES.get(cls_id, "unknown")
                    confidence = float(box.conf)
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    last_detections.append({
                        "label": label,
                        "conf": confidence,
                        "bbox": (x1, y1, x2, y2)
                    })

            if last_detections:
                print(f"\n[{time.strftime('%H:%M:%S')}] Detections:")
                for det in last_detections:
                    print(f"{det['label']} ({det['conf']:.0%})")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] No detections")

        display = frame.copy()
        for det in last_detections:
            x1, y1, x2, y2 = det["bbox"]
            label = det["label"]
            color = get_color(label)
            cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
            cv2.putText(display, f"{label} {det['conf']:.0%}",
                        (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

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
    run_pipeline(source="data/sample_video.mp4", interval=0.1, conf=0.4)