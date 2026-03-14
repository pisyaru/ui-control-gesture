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
- [x] Make macOS capture permission requests runloop-safe on the main thread
- [x] Defer AppKit window creation until after NSApplication startup
- [x] Force all AppKit overlay window updates onto the main thread
- [x] Decouple capture permission loading from accessibility imports
- [x] Mirror right-hand cursor movement to match camera semantics
- [x] Add full-size mirrored skeleton overlay feedback for both hands
- [x] Harden overlay focus and add a terminal-based quit fallback

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
- Reworked capture permission waiting so the main run loop keeps pumping while macOS permission prompts are pending.
- Moved AppKit overlay creation behind NSApplication startup so native windows are not created before the menu bar app is initialized.
- Routed overlay render requests through a main-thread bridge so transcript timers and vision callbacks never touch `NSWindow` off the main thread.
- Split the permission loader by subsystem so missing accessibility bindings no longer collapse camera and microphone status to `unavailable`.
- Mirrored the right-hand cursor mapping and mirrored skeleton projection so horizontal movement matches user expectation.
- Extended hand observations and feedback to carry 21-point hand landmarks, then rendered both hands on a full-screen transparent overlay.
- Added a terminal-visible quit hint and AppKit signal pump so `Ctrl+C` can terminate the app even if the menu bar item is unavailable.
