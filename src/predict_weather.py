import torch
from torchvision import models, transforms
from PIL import Image
import cv2

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

def predict_weather(frame_bgr):
    if _model is None:
        load_weather_model()
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    tensor = _transform(Image.fromarray(rgb)).unsqueeze(0)
    with torch.no_grad():
        idx = _model(tensor).argmax(dim=1).item()
    return CLASSES[idx]

def predict_weather_with_confidence(frame_bgr):
    if _model is None:
        load_weather_model()
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    tensor = _transform(Image.fromarray(rgb)).unsqueeze(0)
    with torch.no_grad():
        logits = _model(tensor)
        probs = torch.softmax(logits, dim=1)[0]
        idx = probs.argmax().item()
    return CLASSES[idx], float(probs[idx])