from ultralytics import YOLO

MODEL_PATH = "runs/detect/nayan_sevak/weights/best.pt"
CONF_THRESHOLD = 0.4
HAZARD_CLASSES = ["pothole"]

model = YOLO(MODEL_PATH)

def get_camera_confidence(frame):
    results = model.predict(
        source=frame,
        conf=CONF_THRESHOLD,
        verbose=False
    )

    highest_confidence = 0.0

    for result in results:
        if result.boxes is None:
            continue

        for box in result.boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            class_name = model.names[class_id]

            if class_name in HAZARD_CLASSES:
                highest_confidence = max(highest_confidence, confidence)

    return highest_confidence

def main():
    source = "data/road_dataset/images/val"

    results = model.predict(
        source=source,
        conf=CONF_THRESHOLD,
        save=True,
        show=False
    )

    for result in results:
        camera_confidence = 0.0

        if result.boxes is not None:
            for box in result.boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                class_name = model.names[class_id]

                if class_name in HAZARD_CLASSES:
                    camera_confidence = max(camera_confidence, confidence)

        print(f"Camera confidence: {camera_confidence:.3f}")

if __name__ == "__main__":
    main()