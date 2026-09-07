from ultralytics import YOLO

#model = YOLO("yolov8n.pt")

MODEL_PATH = "runs/detect/nayan_sevak/weights/best.pt"
DATA_PATH = "data/road_dataset/data.yaml"

model = YOLO(MODEL_PATH)

model.train(
    data=DATA_PATH,
    epochs=30,
    imgsz=320,
    batch=16,
    workers=4,
    name="nayan_sevak",
    cache=True,
    patience=15,
    device="mps"        # for macOS with M chip
)