# Lessons

## 2026-03-14

- When the user adds a gesture detail late, re-check handedness, concurrency, and mutual-exclusion rules instead of treating it as an isolated tweak.
- For mixed-modality input, document which limb or sensor owns each action before writing state-machine code.
- When user-facing docs are added or updated, consider whether a Korean counterpart or cross-linked localized version is expected for this project.
- In PyObjC `NSObject` subclasses, use `objc.super`, not Python `super()`, for `init()` and related Objective-C lifecycle methods.
- On macOS, request camera permission from the app layer before starting OpenCV capture on a worker thread; do not rely on OpenCV to trigger the system prompt.
