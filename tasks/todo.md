# Gesture Control App Implementation

- [x] Re-ground the repo, constraints, and implementation stack
- [x] Lock product decisions for gesture roles, STT modes, language priority, and model defaults
- [x] Scaffold the Python app package, shared config, and task tracking docs
- [x] Build the menu bar shell, settings state, permission checks, and overlay window primitives
- [x] Implement MediaPipe-based hand/head tracking adapters and gesture state machines
- [x] Implement Quartz-based cursor, click, drag, and scroll control
- [x] Implement wake-word STT, fist-hold STT, and transcript placement orchestration
- [x] Implement pluggable STT/TTS adapters and settings model selection
- [x] Add unit tests for gesture mapping and speech coordination
- [x] Run verification checks and record review notes
- [x] Differentiate denied vs not-determined macOS capture permissions and add recovery actions

## Notes

- Right hand controls cursor, click, drag, and fist-STT.
- Left hand provides scroll gestures so the right hand can stay occupied with UI control.
- Head tracking is used for transcript placement, not OS navigation in v1.
- STT priority is Korean first with English and Japanese as secondary support.
- Wake-word and fist-recording modes must be mutually exclusive.

## Review

- Added a Python app shell under `src/ui_control_gesture/` with AppKit menu bar wiring, MediaPipe vision pipeline, Quartz input control, overlay rendering, and modular audio adapters.
- Verified syntax with `python3 -m compileall src tests`.
- Verified logic with `PYTHONPATH=src python3 -m pytest tests/unit -q` and observed `17 passed`.
- Installed `pytest` in the user Python environment because it was not present locally.
- Fixed review findings around wake recognizer self-join, stale wake buffers, STT-off suppression of in-flight wake transcripts, and vision runtime error surfacing.
- Created a repo-local `.venv`, installed runtime dependencies with `pip install -e .`, and downloaded `models/hand_landmarker.task` plus `models/face_landmarker.task`.
- Confirmed `.venv/` and `models/` are ignored by git so only code and docs are pushed.
- Added denied-permission recovery flow that opens the relevant macOS Privacy panes when camera or microphone access has already been rejected.
- Added unit coverage for permission summary text and privacy-settings launch actions.
