<h1 align="center">macClaw</h1>

<p align="center">
  Control your Mac with hand gestures using a webcam, MediaPipe, and Python.
</p>

<p align="center">
  <img src="./MacClaw.png" alt="macClaw" width="760" />
</p>

<p align="center">
  Real-time hand tracking • Smooth cursor control • Pinch to click • Scroll and drag gestures
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="#gesture-controls">Gestures</a> •
  <a href="#requirements">Requirements</a> •
  <a href="#tuning">Tuning</a>
</p>

`macClaw` turns two-hand gestures into desktop actions:
- Left hand selects the current mode
- Right hand controls the cursor or action
- Thumb-index pinch triggers click

## What It Does

- Real-time hand tracking with MediaPipe Hand Landmarker
- Smooth mouse movement mapped from your webcam feed to your screen
- Pinch-to-click interaction
- Gesture-based scrolling
- Gesture-based click-and-drag
- On-screen visual overlay for landmarks, active area, and current mode

## Gesture Controls

The app uses both hands at once:

| Left Hand | Mode | Right Hand Action |
| --- | --- | --- |
| Closed fist | `IDLE` | No desktop input |
| Index finger up | `CURSOR` | Move cursor, pinch to click |
| Index + middle up | `SCROLL` | Move hand vertically to scroll |
| Index + middle + ring up | `DRAG` | Click and drag |

Notes:
- The right hand drives the actual pointer behavior
- The active control zone is limited to the center area of the camera frame for better stability
- Press `q` to quit the app

## Stack

- Python
- OpenCV
- MediaPipe Tasks
- PyAutoGUI
- Quartz (macOS mouse events)

## Requirements

- macOS
- Python 3
- Webcam access
- Accessibility permission for mouse control
- Camera permission for the terminal or Python app you run

Because the project uses `Quartz`, it is currently macOS-focused.

## Quick Start

1. Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install opencv-python mediapipe pyautogui pyobjc-framework-Quartz
```

3. Run the app:

```bash
python3 gesture_hand.py
```

Make sure `hand_landmarker.task` stays in the project root next to `gesture_hand.py`, since the script loads it from the local directory.

## Project Structure

```text
.
├── gesture_hand.py         # Main application loop and gesture logic
├── hand_landmarker.task    # MediaPipe hand tracking model
└── README.md
```

## How It Works

`macClaw` opens your webcam feed, detects up to two hands in real time, and separates responsibilities between them:

- Left hand acts like a mode switch
- Right hand performs movement or actions inside the selected mode
- Cursor motion is smoothed before sending events to macOS
- Clicking uses a pinch threshold with cooldown logic to reduce accidental repeats
- Dragging holds the mouse button down until you leave drag mode

## Tuning

If you want to adjust responsiveness, the main constants live near the top of `gesture_hand.py`:

- `SMOOTH`
- `CLICK_COOLDOWN`
- `PINCH_START_PX`
- `PINCH_RELEASE_PX`
- `SCROLL_THRESHOLD`
- `SCROLL_GAIN`
- `ACTIVE_X_MIN`, `ACTIVE_X_MAX`
- `ACTIVE_Y_MIN`, `ACTIVE_Y_MAX`

These control pointer smoothing, click sensitivity, scroll speed, and the active tracking region.

## Known Notes

- Lighting and webcam angle have a big impact on tracking quality
- The current implementation is designed around one person using one webcam
- If cursor control does not work, re-check macOS Accessibility permissions

## Roadmap Ideas

- Right-click and multi-click gestures
- Gesture calibration mode
- Config file for sensitivity tuning
- Better gesture feedback in the UI
- Cross-platform input support
