"""
Nayan Sevak — Telemetry Worker
Background daemon thread (~4 Hz) that runs the full ML pipeline and exposes
live telemetry + hazard-event history to the Flask/HTTP server.

Design notes
------------
* Cycle target: 250 ms (4 Hz). Logs a warning if any cycle exceeds this.
* All pipeline calls are wrapped in try/except so a missing model or bad
  frame never kills the thread — we fall back to the previous value instead.
* cameraWeight / sensorWeight are stored as whole-number percentages (0-100)
  because fusion_engine() returns them as 0-1 fractions.
* Hazard log records a transition-only entry: only when tier moves from
  NOMINAL → WARNING/CRITICAL does a new row get appended.
* Hazard type heuristic: "pothole" if vibration_class_prob >= ultrasonic_score
  else "obstacle".
* data/ directory is created on first write (os.makedirs … exist_ok=True).
"""

import os
import sys
import json
import time
import uuid
import logging
import threading

# numpy and cv2 are heavy optional deps — imported lazily so the module
# can be imported even in a minimal venv (e.g. Flask-only).
_np = None
_cv2 = None

# ---------------------------------------------------------------------------
# Path bootstrap — resolve src/ directory regardless of CWD
# ---------------------------------------------------------------------------
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

# Deferred imports so missing dependencies/models don't crash at import time.
_detect = None
_predict_weather = None
_vibration_sensor = None
_ultrasonic_sensor = None
_fusion = None

def _lazy_import_pipeline():
    """Import pipeline modules once; suppress ImportError so missing deps are
    non-fatal (worker falls back to mock values)."""
    global _detect, _predict_weather, _vibration_sensor, _ultrasonic_sensor, _fusion
    global _np, _cv2
    try:
        import numpy as _np_mod
        _np = _np_mod
    except Exception as exc:
        logging.warning("[telemetry_worker] numpy import failed: %s", exc)
    try:
        import cv2 as _cv2_mod
        _cv2 = _cv2_mod
    except Exception as exc:
        logging.warning("[telemetry_worker] cv2 import failed: %s", exc)
    try:
        import detect as _detect
    except Exception as exc:
        logging.warning("[telemetry_worker] detect import failed: %s", exc)
    try:
        import predict_weather as _predict_weather
    except Exception as exc:
        logging.warning("[telemetry_worker] predict_weather import failed: %s", exc)
    try:
        import vibration_sensor as _vibration_sensor
    except Exception as exc:
        logging.warning("[telemetry_worker] vibration_sensor import failed: %s", exc)
    try:
        import ultrasonic_sensor as _ultrasonic_sensor
    except Exception as exc:
        logging.warning("[telemetry_worker] ultrasonic_sensor import failed: %s", exc)
    try:
        import fusion as _fusion
    except Exception as exc:
        logging.warning("[telemetry_worker] fusion import failed: %s", exc)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CYCLE_TARGET_S = 0.250          # 4 Hz
SLOW_CYCLE_THRESHOLD_S = 0.250  # log warning if cycle exceeds this
HAZARD_LOG_PATH = "data/hazard_log.json"
HAZARD_LOG_CAP = 200
SAMPLE_VIDEO_PATH = "data/road_dataset/sample_video.mp4"

# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------
_lock = threading.Lock()

_latest_telemetry: dict = {
    "yoloConfidence": 0.0,
    "sensorWeight": 25,        # whole-number %
    "cameraWeight": 75,        # whole-number %
    "fusionScore": 0.0,
    "tier": "NOMINAL",
    "alert": False,
    "mpuVibration": 0.0,
    "ultrasonicDistance": 200.0,
    "rearDistance": 60.0,      # static placeholder (no rear sensor)
    "visibilityScore": 1.0,
    "weather": "sunny",
    "aiFps": 0.0,
    "timestamp": time.time(),
    # Static placeholders — no real data source yet
    "batteryPct": 84,
    "speedKmh": 68,
    "tirePressurePsi": 38,
}

_hazard_log: list = []          # most-recent-first; each entry is a dict

# ---------------------------------------------------------------------------
# Hazard log helpers
# ---------------------------------------------------------------------------

def _load_hazard_log_from_disk() -> list:
    """Load persisted hazard log at startup if the file exists."""
    if not os.path.isfile(HAZARD_LOG_PATH):
        return []
    try:
        with open(HAZARD_LOG_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list):
            logging.info("[telemetry_worker] Loaded %d hazard entries from disk.", len(data))
            return data
    except Exception as exc:
        logging.warning("[telemetry_worker] Could not read hazard log: %s", exc)
    return []


def _persist_hazard_log(log: list) -> None:
    """Write hazard log to disk atomically (tmp → rename). Creates data/ if needed."""
    # Ensure the data directory exists before any write
    os.makedirs(os.path.dirname(HAZARD_LOG_PATH), exist_ok=True)
    tmp_path = HAZARD_LOG_PATH + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(log, fh, indent=2)
        os.replace(tmp_path, HAZARD_LOG_PATH)
    except Exception as exc:
        logging.warning("[telemetry_worker] Failed to persist hazard log: %s", exc)


def _append_hazard_event(tier: str, vibration_class_prob: float,
                          ultrasonic_score: float, ultrasonic_distance: float,
                          combined_confidence: float) -> None:
    """Append one hazard-transition entry and persist. Called under _lock."""
    # Heuristic: if vibration probability dominates → pothole; else → obstacle
    hazard_type = "pothole" if vibration_class_prob >= ultrasonic_score else "obstacle"
    entry = {
        "id": uuid.uuid4().hex,
        "timestamp": time.time(),
        "type": hazard_type,
        "tier": tier,
        "confidence": round(combined_confidence, 4),
        "distance": round(ultrasonic_distance, 1),
    }
    # Prepend (most-recent-first) and cap
    _hazard_log.insert(0, entry)
    if len(_hazard_log) > HAZARD_LOG_CAP:
        del _hazard_log[HAZARD_LOG_CAP:]
    _persist_hazard_log(_hazard_log)

# ---------------------------------------------------------------------------
# Mock data generators (isolated, side-effect free)
# ---------------------------------------------------------------------------

def generate_mock_vibration_window(sample_rate: int = 100,
                                   window_size: int = 100):
    """Return a synthetic accelerometer magnitude window (1-D float64 array).

    Generates low-amplitude road noise with occasional injected shock spikes
    to exercise the full range of vibration_sensor.predict_vibration_probability().
    Returns a plain Python list if numpy is not available.
    """
    if _np is None:
        # Fallback: return a flat list of zeros
        return [0.0] * window_size
    rng = _np.random.default_rng()
    # Baseline road vibration: small Gaussian noise around 0
    baseline = rng.normal(loc=0.0, scale=0.05, size=window_size)
    # ~15% chance of a shock spike (simulated pothole hit)
    if rng.random() < 0.15:
        spike_idx = rng.integers(10, window_size - 10)
        spike_width = rng.integers(3, 8)
        spike_amp = rng.uniform(1.5, 3.5)
        baseline[spike_idx:spike_idx + spike_width] += spike_amp * rng.choice([-1, 1])
    return baseline.astype(_np.float64)


def generate_mock_ultrasonic_reading() -> tuple:
    """Return (distance_cm: float, closing_rate_cm_per_s: float).

    Simulates a front sensor drifting between 50 cm and 250 cm with occasional
    fast-approach events to exercise the full score range.
    Returns safe fallback values if numpy is not available.
    """
    if _np is None:
        return 150.0, 5.0
    rng = _np.random.default_rng()
    # Slowly walk distance with occasional sudden-approach events
    base_distance = rng.uniform(80.0, 220.0)
    if rng.random() < 0.10:
        # Rapid approach scenario
        base_distance = rng.uniform(30.0, 60.0)
        closing_rate = rng.uniform(40.0, 90.0)
    else:
        closing_rate = rng.uniform(-5.0, 15.0)
    return float(_np.clip(base_distance, 20.0, 400.0)), float(closing_rate)

# ---------------------------------------------------------------------------
# Synthetic frame fallback
# ---------------------------------------------------------------------------

def _make_synthetic_frame(width: int = 640, height: int = 480):
    """Return a uint8 BGR frame of random noise — used when the sample video
    cannot be opened. Lets the weather/detection models exercise (badly) rather
    than blocking the pipeline. Returns None if numpy is unavailable."""
    if _np is None:
        return None
    return _np.random.randint(0, 255, (height, width, 3), dtype=_np.uint8)

# ---------------------------------------------------------------------------
# Worker thread
# ---------------------------------------------------------------------------

def _worker_loop(session_start: float) -> None:
    """Main loop — runs until process exits (daemon thread)."""
    global _latest_telemetry, _hazard_log

    _lazy_import_pipeline()

    # Pre-load weather model once (so first cycle isn't abnormally slow)
    if _predict_weather is not None:
        try:
            _predict_weather.load_weather_model()
        except Exception as exc:
            logging.warning("[telemetry_worker] Weather model preload failed: %s", exc)

    # Video capture — loop the sample video
    cap = None
    use_synthetic_frames = False

    def _open_video():
        nonlocal cap, use_synthetic_frames
        if _cv2 is None:
            use_synthetic_frames = True
            logging.warning("[telemetry_worker] cv2 not available, using synthetic frames.")
            return
        c = _cv2.VideoCapture(SAMPLE_VIDEO_PATH)
        if c.isOpened():
            cap = c
            use_synthetic_frames = False
            logging.info("[telemetry_worker] Opened sample video: %s", SAMPLE_VIDEO_PATH)
        else:
            use_synthetic_frames = True
            logging.warning(
                "[telemetry_worker] Sample video not found at '%s'. "
                "Using synthetic frames.",
                SAMPLE_VIDEO_PATH
            )

    _open_video()

    # Carry-forward values (used as fallback on exception)
    prev_cam_conf = 0.0
    prev_weather = "sunny"
    prev_weather_conf = 1.0
    prev_vis_score = 1.0
    prev_vib_prob = 0.0
    prev_us_score = 0.0
    prev_tier = "NOMINAL"

    cycle_count = 0

    while True:
        cycle_start = time.monotonic()

        # ----------------------------------------------------------------
        # 1. Grab frame
        # ----------------------------------------------------------------
        frame = None
        if not use_synthetic_frames and _cv2 is not None:
            ret, frame = cap.read()
            if not ret:
                # End of file — rewind
                cap.set(_cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
                if not ret:
                    logging.warning("[telemetry_worker] Video rewind failed, switching to synthetic.")
                    use_synthetic_frames = True

        if frame is None:
            frame = _make_synthetic_frame()

        # ----------------------------------------------------------------
        # 2. Camera confidence (YOLO)
        # ----------------------------------------------------------------
        camera_confidence = prev_cam_conf
        if _detect is not None:
            try:
                camera_confidence = _detect.get_camera_confidence(frame)
                prev_cam_conf = camera_confidence
            except Exception as exc:
                logging.debug("[telemetry_worker] detect failed: %s", exc)

        # ----------------------------------------------------------------
        # 3. Weather + visibility
        # ----------------------------------------------------------------
        weather = prev_weather
        weather_confidence = prev_weather_conf
        visibility_score = prev_vis_score
        if _predict_weather is not None:
            try:
                weather, weather_confidence, visibility_score = \
                    _predict_weather.predict_weather_with_confidence(frame)
                prev_weather = weather
                prev_weather_conf = weather_confidence
                prev_vis_score = visibility_score
            except Exception as exc:
                logging.debug("[telemetry_worker] predict_weather failed: %s", exc)

        # ----------------------------------------------------------------
        # 4. Vibration (mock window → RF model)
        # ----------------------------------------------------------------
        vibration_class_prob = prev_vib_prob
        vib_window = generate_mock_vibration_window()
        if _vibration_sensor is not None:
            try:
                vibration_class_prob = _vibration_sensor.predict_vibration_probability(vib_window)
                prev_vib_prob = vibration_class_prob
            except Exception as exc:
                logging.debug("[telemetry_worker] vibration_sensor failed: %s", exc)

        # ----------------------------------------------------------------
        # 5. Ultrasonic (mock reading → score)
        # ----------------------------------------------------------------
        ultrasonic_score = prev_us_score
        ultrasonic_distance, closing_rate = generate_mock_ultrasonic_reading()
        if _ultrasonic_sensor is not None:
            try:
                ultrasonic_score = _ultrasonic_sensor.calculate_ultrasonic_score(
                    ultrasonic_distance, closing_rate
                )
                prev_us_score = ultrasonic_score
            except Exception as exc:
                logging.debug("[telemetry_worker] ultrasonic_sensor failed: %s", exc)

        # ----------------------------------------------------------------
        # 6. Fusion
        # ----------------------------------------------------------------
        fusion_result = {
            "combined_confidence": 0.0,
            "alert": False,
            "tier": "NOMINAL",
            "camera_weight": 0.75,
            "sensor_weight": 0.25,
            "sensor_score": 0.0,
        }
        if _fusion is not None:
            try:
                fusion_result = _fusion.fusion_engine(
                    camera_confidence=camera_confidence,
                    vibration_class_prob=vibration_class_prob,
                    ultrasonic_score=ultrasonic_score,
                    visibility_score=visibility_score,
                )
            except Exception as exc:
                logging.debug("[telemetry_worker] fusion failed: %s", exc)

        current_tier = fusion_result["tier"]
        combined_confidence = fusion_result["combined_confidence"]

        # ----------------------------------------------------------------
        # 7. Hazard event — log on tier TRANSITION into warning/critical only
        # ----------------------------------------------------------------
        if current_tier in ("WARNING", "CRITICAL") and prev_tier == "NOMINAL":
            with _lock:
                _append_hazard_event(
                    tier=current_tier,
                    vibration_class_prob=vibration_class_prob,
                    ultrasonic_score=ultrasonic_score,
                    ultrasonic_distance=ultrasonic_distance,
                    combined_confidence=combined_confidence,
                )

        prev_tier = current_tier

        # ----------------------------------------------------------------
        # 8. Measure AI throughput
        # ----------------------------------------------------------------
        cycle_elapsed = time.monotonic() - cycle_start
        ai_fps = round(1.0 / cycle_elapsed, 1) if cycle_elapsed > 0 else 0.0

        if cycle_elapsed > SLOW_CYCLE_THRESHOLD_S:
            logging.warning(
                "[telemetry_worker] Cycle %d took %.0f ms (target ≤ %d ms)",
                cycle_count,
                cycle_elapsed * 1000,
                int(SLOW_CYCLE_THRESHOLD_S * 1000),
            )

        # ----------------------------------------------------------------
        # 9. Write to shared telemetry dict
        #    cameraWeight / sensorWeight: convert 0-1 fractions → whole-number %
        # ----------------------------------------------------------------
        with _lock:
            _latest_telemetry.update({
                "yoloConfidence": round(camera_confidence * 100.0, 1),
                "cameraWeight": round(fusion_result["camera_weight"] * 100.0),
                "sensorWeight": round(fusion_result["sensor_weight"] * 100.0),
                "fusionScore": round(combined_confidence * 100.0, 1),
                "tier": current_tier,
                "alert": fusion_result["alert"],
                "mpuVibration": round(float(_np.max(_np.abs(vib_window))), 3) if _np is not None and hasattr(vib_window, '__len__') else 0.0,
                "ultrasonicDistance": round(ultrasonic_distance, 1),
                "visibilityScore": round(visibility_score, 3),
                "weather": weather,
                "aiFps": ai_fps,
                "timestamp": time.time(),
            })

        # ----------------------------------------------------------------
        # 10. Sleep remainder of cycle (skip if cycle already overran)
        # ----------------------------------------------------------------
        sleep_s = CYCLE_TARGET_S - (time.monotonic() - cycle_start)
        if sleep_s > 0:
            time.sleep(sleep_s)

        cycle_count += 1

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
_worker_thread: threading.Thread | None = None
_session_start: float = 0.0


def start_worker() -> None:
    """Start the background telemetry thread. Safe to call only once."""
    global _worker_thread, _session_start, _hazard_log

    if _worker_thread is not None and _worker_thread.is_alive():
        logging.warning("[telemetry_worker] start_worker() called but thread already running.")
        return

    # Load persisted hazard log from disk so history survives restarts
    _hazard_log = _load_hazard_log_from_disk()
    _session_start = time.time()

    _worker_thread = threading.Thread(
        target=_worker_loop,
        args=(_session_start,),
        name="TelemetryWorker",
        daemon=True,
    )
    _worker_thread.start()
    logging.info("[telemetry_worker] Worker thread started (target %.0f ms / cycle).",
                 CYCLE_TARGET_S * 1000)


def get_latest_telemetry() -> dict:
    """Return a snapshot of the latest telemetry dict (thread-safe copy)."""
    with _lock:
        return dict(_latest_telemetry)


def get_hazard_log() -> list:
    """Return the in-memory hazard log as a list copy (most-recent-first)."""
    with _lock:
        return list(_hazard_log)


def get_trip_summary() -> dict:
    """Return computed aggregates for the current session.

    NOTE: distance_km is intentionally null — no real GPS source exists yet.
    Do NOT populate it with fabricated numbers. This comment is here so the
    field is not mistaken for a missing-data bug in a future review.
    """
    with _lock:
        log_snapshot = list(_hazard_log)

    total = len(log_snapshot)
    by_type: dict = {}
    for entry in log_snapshot:
        t = entry.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    duration_s = time.time() - _session_start if _session_start else 0.0

    return {
        "total_hazards": total,
        "by_type": by_type,
        "duration_seconds": round(duration_s, 1),
        "session_start": _session_start,
        # GPS / route data not available — do not fabricate
        "distance_km": None,
        "route": None,
    }
