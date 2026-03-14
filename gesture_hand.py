import cv2
import mediapipe as mp
import math
import time

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Hand connections (21 landmarks, pairs defining the skeleton)
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),       # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),       # Index finger
    (0, 9), (9, 10), (10, 11), (11, 12),   # Middle finger
    (0, 13), (13, 14), (14, 15), (15, 16), # Ring finger
    (0, 17), (17, 18), (18, 19), (19, 20), # Pinky
    (5, 9), (9, 13), (13, 17),             # Palm
]

# Store latest result from async callback
latest_result = None


def is_finger_up(lm, tip_id, base_id):
    return lm[tip_id].y < lm[base_id].y


def dist(lm, a, b, w, h):
    return math.hypot(
        (lm[a].x - lm[b].x) * w,
        (lm[a].y - lm[b].y) * h,
    )


def classify(lm, w, h):
    if dist(lm, 4, 8, w, h) < 30:
        return "CLICK"

    iu = is_finger_up(lm, 8, 6)
    mu = is_finger_up(lm, 12, 10)
    ru = is_finger_up(lm, 16, 14)
    pu = is_finger_up(lm, 20, 18)

    if iu and mu and ru and pu:
        return "FREEZE"
    if iu and mu and not ru and not pu:
        return "SHORTCUT"
    if iu and not mu:
        return "MOVE"
    return "NONE"


def result_callback(result, output_image, timestamp_ms):
    global latest_result
    latest_result = result

# Set up HandLandmarker in LIVE_STREAM mode
base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.LIVE_STREAM,
    num_hands=1,
    min_hand_detection_confidence=0.7,
    min_tracking_confidence=0.5,
    result_callback=result_callback
)

cap = cv2.VideoCapture(0)

with vision.HandLandmarker.create_from_options(options) as landmarker:
    while cap.isOpened():
        success, image = cap.read()
        if not success:
            print("Ignoring empty camera frame.")
            break

        frame = cv2.flip(image, 1)

        # Convert BGR to RGB and create MediaPipe Image
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Send frame for async detection
        timestamp_ms = int(time.time() * 1000)
        landmarker.detect_async(mp_image, timestamp_ms)

        # Draw landmarks from latest result
        if latest_result and latest_result.hand_landmarks:
            for hand_landmarks in latest_result.hand_landmarks:
                h, w, _ = frame.shape
                gesture = classify(hand_landmarks, w, h)
                points = []
                for lm in hand_landmarks:
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    points.append((cx, cy))
                    cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)

                # Draw connections
                for start_idx, end_idx in HAND_CONNECTIONS:
                    if start_idx < len(points) and end_idx < len(points):
                        cv2.line(frame, points[start_idx], points[end_idx], (0, 255, 0), 2)

                cv2.putText(
                    frame,
                    gesture,
                    (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.2,
                    (0, 220, 100),
                    2,
                )

        cv2.imshow("Hand Gesture Recognition", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
