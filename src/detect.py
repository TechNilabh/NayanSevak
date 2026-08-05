from ultralytics import YOLO

model = YOLO("runs/detect/nayan_sevak/weights/best.pt")

results = model.predict(
    source="data/road_dataset/images/val",
    conf=0.4,
    save=True,
    show=False
)