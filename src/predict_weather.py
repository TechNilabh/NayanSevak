import numpy as np
import torch
import cv2
from torchvision import models, transforms
from PIL import Image

CLASSES = ["foggy", "rainy", "snowy", "sunny"]
MODEL_PATH = "runs/weather/best_weather.pt"

_model = None
_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

def load_weather_model(path=MODEL_PATH):
    global _model
    model = models.mobilenet_v3_small(weights=None)
    in_features = model.classifier[3].in_features
    model.classifier[3] = torch.nn.Linear(in_features, len(CLASSES))
    model.load_state_dict(torch.load(path, map_location="cpu"))
    model.eval()
    _model = model
    return _model

def preprocess(frame_bgr):
    if _model is None:
        load_weather_model()
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(rgb)
    return _transform(image).unsqueeze(0)

def calculate_visibility_score(frame_bgr):
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    brightness = np.mean(gray)
    contrast = np.std(gray)
    brightness_score = brightness / 255.0
    contrast_score = min(contrast / 64.0, 1.0)
    visibility_score = ((0.5 * brightness_score) + (0.5 * contrast_score))
    return float(np.clip(visibility_score, 0.0, 1.0))

def predict_weather(frame_bgr):
    tensor = preprocess(frame_bgr)
    with torch.no_grad():
        idx = _model(tensor).argmax(dim=1).item()
    weather = CLASSES[idx]
    return weather

def predict_weather_with_confidence(frame_bgr):
    tensor = preprocess(frame_bgr)
    with torch.no_grad():
        logits = _model(tensor)
        probs = torch.softmax(logits, dim=1)[0]
    idx = int(probs.argmax().item())
    weather = CLASSES[idx]
    weather_confidence = float(probs[idx])
    visibility_score = calculate_visibility_score(frame_bgr)
    return weather, weather_confidence, visibility_score

if __name__ == "__main__":
    image_path = "data/weather_dataset/sunny/00024.jpg"

    frame = cv2.imread(image_path)

    if frame is None:
        raise ValueError(f"Could not read image: {image_path}")

    weather, weather_confidence, visibility_score = predict_weather_with_confidence(frame)

    print(f"Weather: {weather}")
    print(f"Weather confidence: {weather_confidence:.3f}")
    print(f"Visibility score: {visibility_score:.3f}")