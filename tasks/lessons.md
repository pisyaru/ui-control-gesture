# Lessons

## 2026-03-14

- When the user adds a gesture detail late, re-check handedness, concurrency, and mutual-exclusion rules instead of treating it as an isolated tweak.
- For mixed-modality input, document which limb or sensor owns each action before writing state-machine code.
- When user-facing docs are added or updated, consider whether a Korean counterpart or cross-linked localized version is expected for this project.
- In PyObjC `NSObject` subclasses, use `objc.super`, not Python `super()`, for `init()` and related Objective-C lifecycle methods.
- On macOS, request camera permission from the app layer before starting OpenCV capture on a worker thread; do not rely on OpenCV to trigger the system prompt.
- For macOS TCC permissions, treat `denied` as a separate UX path from `not_determined`; once access was denied, the app must direct the user to System Settings instead of waiting for another prompt.
- When waiting for macOS AVFoundation permission callbacks on the main thread, keep the AppKit run loop pumping; blocking with `Event.wait()` can prevent the prompt and callback from completing.
- Do not create `NSWindow` or other AppKit UI objects before `NSApplication.sharedApplication()` exists and the menu-bar app has entered its startup lifecycle.
