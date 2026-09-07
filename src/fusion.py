import numpy as np

ALERT_THRESHOLD = 0.6
WARNING_THRESHOLD = ALERT_THRESHOLD * 0.65


def _get_tier(combined_confidence):
    if combined_confidence >= ALERT_THRESHOLD:
        return "CRITICAL"
    elif combined_confidence >= WARNING_THRESHOLD:
        return "WARNING"
    return "NOMINAL"


def fusion_engine(camera_confidence, vibration_class_prob, ultrasonic_score, visibility_score):
    camera_confidence = np.clip(camera_confidence, 0.0, 1.0)
    vibration_class_prob = np.clip(vibration_class_prob, 0.0, 1.0)
    ultrasonic_score = np.clip(ultrasonic_score, 0.0, 1.0)
    visibility_score = np.clip(visibility_score, 0.0, 1.0)

    sensor_score = max(vibration_class_prob, ultrasonic_score)

    if visibility_score > 0.6:
        w_camera = 0.75
        w_sensor = 0.25
    else:
        w_camera = 0.20
        w_sensor = 0.80

    combined_confidence = w_camera * camera_confidence + w_sensor * sensor_score
    alert = combined_confidence > ALERT_THRESHOLD
    tier = _get_tier(combined_confidence)

    return {
        "combined_confidence": float(combined_confidence),
        "alert": bool(alert),
        "tier": tier,
        "camera_weight": w_camera,
        "sensor_weight": w_sensor,
        "sensor_score": float(sensor_score),
    }


if __name__ == "__main__":
    camera_confidence = 0.85
    vibration_class_prob = 0.70
    ultrasonic_score = 0.40
    visibility_score = 0.80

    result = fusion_engine(camera_confidence, vibration_class_prob, ultrasonic_score, visibility_score)

    print(f"Camera confidence: {camera_confidence:.3f}")
    print(f"Vibration probability: {vibration_class_prob:.3f}")
    print(f"Ultrasonic score: {ultrasonic_score:.3f}")
    print(f"Visibility score: {visibility_score:.3f}")
    print(f"Combined confidence: {result['combined_confidence']:.3f}")
    print(f"Camera weight: {result['camera_weight']:.2f}")
    print(f"Sensor weight: {result['sensor_weight']:.2f}")
    print(f"Tier: {result['tier']}")
    print(f"Alert: {result['alert']}")