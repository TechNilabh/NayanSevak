from ultralytics import YOLO

model = YOLO("runs/detect/car_vigilanty_model/weights/best.pt")

results = model.predict(
    source="data/images/val",
    conf=0.4,
    save=True,
    show=False
)