from ultralytics import YOLO

#model = YOLO("yolov8n.pt")
model = YOLO("runs/detect/nayan_sevak/weights/best.pt")

model.train(
    data="data/road_dataset/data.yaml",
    epochs=30,
    imgsz=320,
    batch=16,
    workers=4,
    name="nayan_sevak",
    cache=True,
    patience=15,
    device="mps"        # for macOS with M chip
)