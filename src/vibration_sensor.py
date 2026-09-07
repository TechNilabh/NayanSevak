import os
import glob
import numpy as np
import pandas as pd
import joblib

from scipy.signal import butter, filtfilt
from scipy.stats import kurtosis, skew
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

DATASET_DIR = "data/sensor_dataset"
MODEL_PATH = "runs/sensor/vibration_rf.joblib"

SAMPLE_RATE = 100
WINDOW_SIZE = 100
HOP_SIZE = 50

LOW_CUTOFF = 0.5
HIGH_CUTOFF = 20.0

def bandpass_filter(signal, lowcut, highcut, fs, order=4):
    nyquist = fs / 2
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype="band")
    return filtfilt(b, a, signal)

def fft_band_energy(signal, fs, low_freq, high_freq):
    n = len(signal)
    fft_values = np.fft.rfft(signal)
    frequencies = np.fft.rfftfreq(n, d=1 / fs)
    power = np.abs(fft_values) ** 2
    mask = (frequencies >= low_freq) & (frequencies < high_freq)
    return np.sum(power[mask])

def extract_features(window):
    mean = np.mean(window)
    std = np.std(window)
    rms = np.sqrt(np.mean(window ** 2))
    peak = np.max(np.abs(window))
    peak_to_peak = np.max(window) - np.min(window)
    kurt = kurtosis(window)
    skewness = skew(window)
    zero_crossings = np.sum(np.diff(np.signbit(window)))
    zcr = zero_crossings / len(window)
    fft_0_5 = fft_band_energy(window, SAMPLE_RATE, 0, 5)
    fft_5_10 = fft_band_energy(window, SAMPLE_RATE, 5, 10)
    fft_10_20 = fft_band_energy(window, SAMPLE_RATE, 10, 20)
    return [mean, std, rms, peak, peak_to_peak, kurt, skewness, zcr, fft_0_5, fft_5_10, fft_10_20]

def process_file(filepath):
    df = pd.read_csv(filepath)
    required_columns = ["ax", "ay", "az", "label"]
    for column in required_columns:
        if column not in df.columns:
            raise ValueError(f"Missing column '{column}' in {filepath}")
    ax = df["ax"].to_numpy(dtype=np.float64)
    ay = df["ay"].to_numpy(dtype=np.float64)
    az = df["az"].to_numpy(dtype=np.float64)
    magnitude = np.sqrt(ax ** 2 + ay ** 2 + az ** 2)
    magnitude = magnitude - np.mean(magnitude)
    if len(magnitude) < WINDOW_SIZE:
        return []
    filtered_signal = bandpass_filter(magnitude, LOW_CUTOFF, HIGH_CUTOFF, SAMPLE_RATE)
    samples = []
    for start in range(0, len(filtered_signal) - WINDOW_SIZE + 1, HOP_SIZE):
        end = start + WINDOW_SIZE
        window = filtered_signal[start:end]
        features = extract_features(window)
        window_labels = df["label"].values[start:end]
        label = int(pd.Series(window_labels).mode()[0])
        samples.append(features + [label])
    return samples

def load_dataset():
    filepath = os.path.join(DATASET_DIR, "vibration_data.csv")
    print(f"Processing: {filepath}")
    samples = process_file(filepath)
    return np.array(samples, dtype=float)

def train_model():
    data = load_dataset()
    if len(data) == 0:
        raise ValueError("No data found!")

    X = data[:, :-1]
    y = data[:, -1].astype(int)

    print(f"Total windows: {len(X)}")
    print(f"Feature count: {X.shape[1]}")

    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.30, stratify=y, random_state=42)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.50, stratify=y_temp, random_state=42)

    print(f"Training: {len(X_train)}")
    print(f"Validation: {len(X_val)}")
    print(f"Testing: {len(X_test)}")

    model = RandomForestClassifier(n_estimators=150, max_depth=10, class_weight="balanced", random_state=42, n_jobs=-1)

    print("Training model...")
    model.fit(X_train, y_train)

    validation_prediction = model.predict(X_val)
    print("===== VALIDATION =====")
    print(classification_report(y_val, validation_prediction, target_names=["Normal", "Pothole", "Speed-breaker"]))

    test_prediction = model.predict(X_test)
    print("===== TEST =====")
    print(classification_report(y_test, test_prediction, target_names=["Normal", "Pothole", "Speed-breaker"]))

    print("Confusion Matrix:")
    print(confusion_matrix(y_test, test_prediction))

    feature_names = ["Mean", "Std", "RMS", "Peak", "Peak-to-Peak", "Kurtosis", "Skewness", "Zero Crossing Rate", "FFT 0-5 Hz", "FFT 5-10 Hz", "FFT 10-20 Hz"]
    print("===== FEATURE IMPORTANCE =====")
    importance = model.feature_importances_
    for name, value in sorted(zip(feature_names, importance), key=lambda x: x[1], reverse=True):
        print(f"{name:20s}: {value:.4f}")

    joblib.dump(model, MODEL_PATH)
    print(f"Model saved as: {MODEL_PATH}")
    
_vibration_model = None

def predict_vibration_probability(window):
    """Return pothole-class probability [0, 1]. Lazy-loads the RF model once.
    Returns 0.0 if the model file does not exist yet (pre-training state)."""
    global _vibration_model
    try:
        if _vibration_model is None:
            _vibration_model = joblib.load(MODEL_PATH)
        features = extract_features(window)
        probabilities = _vibration_model.predict_proba([features])[0]
        classes = _vibration_model.classes_
        pothole_probability = 0.0
        for class_id, probability in zip(classes, probabilities):
            if int(class_id) == 1:
                pothole_probability = float(probability)
        return pothole_probability
    except FileNotFoundError:
        return 0.0
    except Exception:
        return 0.0

if __name__ == "__main__":
    train_model()