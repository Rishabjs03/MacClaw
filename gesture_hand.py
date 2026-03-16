import cv2
import mediapipe as mp
import math
import pyautogui
import time
import Quartz

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


latest_result = None

SCREEN_W, SCREEN_H = pyautogui.size()
SMOOTH = 0.25
CLICK_COOLDOWN = 0.5
PINCH_START_PX = 42
PINCH_RELEASE_PX = 58
SCROLL_THRESHOLD = 0.01
SCROLL_GAIN = 900
ACTIVE_X_MIN = 0.15
ACTIVE_X_MAX = 0.85
ACTIVE_Y_MIN = 0.15
ACTIVE_Y_MAX = 0.85
smooth_x, smooth_y = SCREEN_W / 2, SCREEN_H / 2
last_click_time = 0.0
last_scroll_y = None
pinch_active = False
drag_active = False
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0


def is_finger_up(lm, tip_id, base_id):
    return lm[tip_id].y < lm[base_id].y


def dist(lm, a, b, w, h):
    return math.hypot(
        (lm[a].x - lm[b].x) * w,
        (lm[a].y - lm[b].y) * h,
    )


def is_pinching(lm, w, h):
    global pinch_active

    pinch_distance = dist(lm, 4, 8, w, h)
    if pinch_active:
        if pinch_distance > PINCH_RELEASE_PX:
            pinch_active = False
        else:
            return True

    if pinch_distance < PINCH_START_PX:
        pinch_active = True
        return True

    return False


def classify(lm, w, h):
    if is_pinching(lm, w, h):
        return "CLICK"

    iu = is_finger_up(lm, 8, 6)
    mu = is_finger_up(lm, 12, 10)
    ru = is_finger_up(lm, 16, 14)
    pu = is_finger_up(lm, 20, 18)

    if iu and mu and ru and pu:
        return "FREEZE"
    if iu and mu and ru and not pu:
        return "SCROLL"
    if iu and not mu:
        return "MOVE"
    return "NONE"


def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


def to_screen(lm):
    x = clamp((lm[8].x - ACTIVE_X_MIN) / (ACTIVE_X_MAX - ACTIVE_X_MIN), 0.0, 1.0)
    y = clamp((lm[8].y - ACTIVE_Y_MIN) / (ACTIVE_Y_MAX - ACTIVE_Y_MIN), 0.0, 1.0)
    return int(x * SCREEN_W), int(y * SCREEN_H)


def move_cursor(tx, ty):
    global smooth_x, smooth_y
    smooth_x += (tx - smooth_x) * SMOOTH
    smooth_y += (ty - smooth_y) * SMOOTH
    pyautogui.moveTo(int(smooth_x), int(smooth_y), duration=0)


def drag_move(tx, ty):
    global smooth_x, smooth_y
    smooth_x += (tx - smooth_x) * SMOOTH
    smooth_y += (ty - smooth_y) * SMOOTH
    event = Quartz.CGEventCreateMouseEvent(
        None,
        Quartz.kCGEventLeftMouseDragged,
        (smooth_x, smooth_y),
        Quartz.kCGMouseButtonLeft,
    )
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)


def trigger_click():
    global last_click_time
    now = time.monotonic()
    if now - last_click_time > CLICK_COOLDOWN:
        pyautogui.click()
        last_click_time = now


def handle_click(lm):
    move_cursor(*to_screen(lm))
    trigger_click()


def scroll_page(lm):
    global last_scroll_y
    current_y = (lm[9].y + lm[12].y) / 2

    if last_scroll_y is None:
        last_scroll_y = current_y
        return

    delta = current_y - last_scroll_y
    if abs(delta) > SCROLL_THRESHOLD:
        pyautogui.scroll(int(-delta * SCROLL_GAIN))
        last_scroll_y = current_y


def reset_modes(gesture):
    global last_scroll_y, pinch_active, drag_active

    if gesture != "CLICK":
        pinch_active = False
    if gesture != "SCROLL":
        last_scroll_y = None
    if gesture != "DRAG" and drag_active:
        pyautogui.mouseUp()
        drag_active = False


def route_action(gesture, lm):
    reset_modes(gesture)

    if gesture == "MOVE":
        move_cursor(*to_screen(lm))
    elif gesture == "CLICK":
        handle_click(lm)
    elif gesture == "SCROLL":
        scroll_page(lm)
    elif gesture == "FREEZE":
        pass


def get_hands(result):
    left_lm, right_lm = None, None
    if not result or not result.hand_landmarks:
        return left_lm, right_lm
    for i, handedness in enumerate(result.handedness):
        label = handedness[0].category_name
        if label == "Left":
            right_lm = result.hand_landmarks[i]
        else:
            left_lm = result.hand_landmarks[i]
    return left_lm, right_lm


from collections import deque
mode_buffer = deque(maxlen=8) 

def stable_mode(raw_mode):
    mode_buffer.append(raw_mode)
    if mode_buffer.count(raw_mode) == len(mode_buffer):
        return raw_mode
    return max(set(mode_buffer), key=mode_buffer.count)


def classify_mode(lm):
    if lm is None:
        return "IDLE"
    iu = is_finger_up(lm, 8,  6)
    mu = is_finger_up(lm, 12, 10)
    ru = is_finger_up(lm, 16, 14)
    pu = is_finger_up(lm, 20, 18)
    if not iu and not mu and not ru and not pu:  return "IDLE"    
    if iu and not mu and not ru and not pu:       return "CURSOR"  
    if iu and mu and not ru and not pu:           return "SCROLL"  
    if iu and mu and ru and not pu:              return "DRAG"    
    return "IDLE"


def result_callback(result, output_image, timestamp_ms):
    global latest_result
    latest_result = result

# Set up HandLandmarker in LIVE_STREAM mode
base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.LIVE_STREAM,
    num_hands=2,
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

       
        if latest_result and latest_result.hand_landmarks:
            h, w, _ = frame.shape

            
            left_lm, right_lm = get_hands(latest_result)

            
            raw_mode     = classify_mode(left_lm)
            current_mode = stable_mode(raw_mode)

            
            reset_modes(current_mode)

            if right_lm is not None and current_mode != "IDLE":
                if current_mode == "CURSOR":
                    move_cursor(*to_screen(right_lm))
                    if is_pinching(right_lm, w, h):
                        trigger_click()
                elif current_mode == "SCROLL":
                    scroll_page(right_lm)
                elif current_mode == "DRAG":
                    if not drag_active:
                        move_cursor(*to_screen(right_lm))
                        pyautogui.mouseDown()
                        drag_active = True
                    else:
                        drag_move(*to_screen(right_lm))

           
            for hand_landmarks in latest_result.hand_landmarks:
                points = []
                for lm in hand_landmarks:
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    points.append((cx, cy))
                    cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)
                for start_idx, end_idx in HAND_CONNECTIONS:
                    cv2.line(frame, points[start_idx], points[end_idx], (0, 255, 0), 2)

            
            box_start = (int(ACTIVE_X_MIN * w), int(ACTIVE_Y_MIN * h))
            box_end   = (int(ACTIVE_X_MAX * w), int(ACTIVE_Y_MAX * h))
            cv2.rectangle(frame, box_start, box_end, (255, 180, 0), 2)
            cv2.putText(frame, f"MODE: {current_mode}", (10, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 220, 100), 2)

        else:
            reset_modes("NONE")

        cv2.imshow("Hand Gesture Recognition", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
