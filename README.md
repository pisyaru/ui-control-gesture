# ui-control-gesture

Camera-driven macOS control app using MediaPipe hand/head tracking plus modular STT/TTS backends.

한국어 문서: [README.ko.md](README.ko.md)

## Planned capabilities

- Right-hand cursor move, left/right click, drag, and fist-triggered STT
- Left-hand middle-finger swipe scrolling while the right hand remains available for pointer work
- Head rotation tracking for transcript placement
- Always-on wake-word STT with pluggable ASR backends
- Pluggable TTS backends for future automation
- Menu bar controls for hand/head/STT/TTS toggles and calibration
- Menu bar camera selection for choosing which macOS camera device to use

## Tech stack

- Python 3.12
- MediaPipe Tasks Vision
- PyObjC / AppKit / Quartz
- OpenCV
- MLX-Audio

## Run

Repository root:

```bash
cd /Users/ijin-yeong/Desktop/1_Programming/ui-control-gesture
```

1. Create a local virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

2. Download the required MediaPipe task models into `models/`:

```bash
mkdir -p models
curl -L https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task -o models/hand_landmarker.task
curl -L https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task -o models/face_landmarker.task
```

3. Launch the app from the repo root:

```bash
source .venv/bin/activate
PYTHONPATH=src python3 -m ui_control_gesture
```

## Notes

- The app is designed for Apple Silicon macOS.
- Accessibility, input monitoring, camera, and microphone permissions are required.
- On first launch the app requests camera and microphone access before starting tracking.
- If no camera or microphone prompt appears, macOS has usually already denied access for the current terminal app or Python. Use the menu bar actions `Open Camera Settings` and `Open Microphone Settings`, enable access in `Privacy & Security`, then relaunch the app.
- STT/TTS backends are local-first and swappable behind adapter interfaces.
- `.venv/` and `models/` are intentionally local-only and ignored by git.
- If large binary assets ever need to be shared, use GitHub Release assets rather than normal git history.
