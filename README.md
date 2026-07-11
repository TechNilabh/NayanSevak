# Nayan Sevak

A lightweight real-time driver assistance system that detects **potholes** and **road signs** from dashcam footage using YOLOv8 and OpenCV. Designed for adverse driving conditions including poor visibility, damaged roads, and variable lighting.

---

## Overview

This project builds a unified computer vision pipeline that:

- Uses a dataset containing various roadsign and pothole images
- Trains a YOLOv8n model to detect 16 classes simultaneously
- Runs real-time inference on dashcam video or webcam feed
- Provides a modular pipeline ready for web deployment via Flask

---

## Project Structure

```
Nayan-Sevak/
│
├── data/
│   ├── images/
│   │   ├── train/
│   │   └── val/
│   ├── labels/
│   │   ├── train/
│   │   └── val/
│   ├── data.yaml
│   └── sample_pothole_video.mp4
│
├── src/
│   ├── train.py
│   ├── detect.py
│   └── pipeline.py
│
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Classes Detected

| ID | Class | ID | Class |
|----|-------|----|-------|
| 0 | pothole | 8 | Speed Limit 30 |
| 1 | Green Light | 9 | Speed Limit 40 |
| 2 | Red Light | 10 | Speed Limit 50 |
| 3 | Speed Limit 10 | 11 | Speed Limit 60 |
| 4 | Speed Limit 100 | 12 | Speed Limit 70 |
| 5 | Speed Limit 110 | 13 | Speed Limit 80 |
| 6 | Speed Limit 120 | 14 | Speed Limit 90 |
| 7 | Speed Limit 20 | 15 | Stop |

---

## Model Performance

Trained on YOLOv8n — 30 epochs, `imgsz=320`, Apple M2 (MPS)

| Metric | Score |
|--------|-------|
| mAP50 (all classes) | 0.878 |
| mAP50-95 | 0.743 |
| Stop Sign | 0.988 |
| Speed Limits (avg) | ~0.930 |
| Pothole | 0.681 |
| Training Time | ~1 hour |

---

## Datasets

Download the dataset:
[Download data.zip] https://drive.google.com/drive/folders/1q1mu2xoAmQTpRFTFVCF0GX-8Ja0kNT99?usp=sharing

After downloading, extract into the project root:
```bash
unzip data.zip
```

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/TechNilabh/NayanSevak.git
cd Nayan-Sevak
```

### 2. Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Prepare datasets

Download from the link in the Datasets section

### 5. Train the model

```bash
python3 src/train.py
```

### 6. Test on a single image or folder

```bash
python3 src/detect.py
```

### 7. Run real-time pipeline

```bash
python3 src/pipeline.py
```

---

## Pipeline

The pipeline reads from a video file or webcam, runs YOLOv8 inference at a configurable interval, draws bounding boxes with confidence scores, and prints timestamped alerts to the terminal.

To switch between video file and webcam, edit the last line of `src/pipeline.py`:

```python
run_pipeline(source="data/sample_pothole_video.mp4", interval=0.1, conf=0.4)

run_pipeline(source=0, interval=0.1, conf=0.4)
```

---

## Tech Stack

- Python 3.14
- YOLOv8 (Ultralytics)
- OpenCV
- PyTorch (MPS backend — Apple Silicon)
- Flask (web deployment — coming soon)
