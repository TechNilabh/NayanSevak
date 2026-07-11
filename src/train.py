from ultralytics import YOLO

model = YOLO("yolov8n.pt")

model.train(
    data="data/data.yaml",
    epochs=30,
    imgsz=320,
    batch=16,
    workers=4,
    name="car_vigilanty_model",
    cache=True,
    device="mps"        # for macOS with M chip
)