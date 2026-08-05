import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from torchvision import models, transforms, datasets

DATA_DIR = "data/weather_dataset"
CLASSES = ["foggy", "rainy", "snowy", "sunny"]
EPOCHS = 15
BATCH_SIZE = 32
DEVICE = "mps"
OUTPUT_PATH = "runs/weather/best_weather.pt"

train_transform = transforms.Compose([
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(10),
    transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
    transforms.ColorJitter(brightness=0.1, saturation=0.1),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

val_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

full_dataset = datasets.ImageFolder(DATA_DIR)
train_size = int(0.8 * len(full_dataset))
val_size = len(full_dataset) - train_size
train_subset, val_subset = random_split(full_dataset, [train_size, val_size])

train_subset.dataset.transform = train_transform
val_subset.dataset.transform = val_transform

train_loader = DataLoader(train_subset, batch_size=BATCH_SIZE, shuffle=True)
val_loader = DataLoader(val_subset, batch_size=BATCH_SIZE)

model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
for param in model.parameters():
    param.requires_grad = False
in_features = model.classifier[3].in_features
model.classifier[3] = nn.Linear(in_features, len(CLASSES))
model.to(DEVICE)

criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.classifier[3].parameters(), lr=1e-3)

best_acc = 0.0
for epoch in range(EPOCHS):
    model.train()
    for images, labels in train_loader:
        images, labels = images.to(DEVICE), labels.to(DEVICE)
        optimizer.zero_grad()
        loss = criterion(model(images), labels)
        loss.backward()
        optimizer.step()

    model.eval()
    correct, total = 0, 0
    with torch.no_grad():
        for images, labels in val_loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            preds = model(images).argmax(dim=1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)
    acc = correct / total
    print(f"Epoch {epoch+1}/{EPOCHS} — val accuracy: {acc:.3f}")

    if acc > best_acc:
        best_acc = acc
        torch.save(model.state_dict(), OUTPUT_PATH)

print(f"Best val accuracy: {best_acc:.3f} — saved to {OUTPUT_PATH}")