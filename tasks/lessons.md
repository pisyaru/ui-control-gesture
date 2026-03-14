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
- Any AppKit `NSWindow` show/hide/update call triggered by timers, vision callbacks, or worker threads must be marshaled back to the main thread first.
- When a mixed dependency loader spans unrelated macOS frameworks, isolate imports by subsystem; one missing module must not collapse unrelated permission paths like camera status.
- For local runtime bugs, verify the fix with direct environment probes first; do not hand the first validation step back to the user.
- For gesture-visualization requests, do not default to a tiny HUD; confirm whether the user wants a full mirrored body-part overlay that matches real perceived size and position.
- A visible macOS status item does not prove the menu is wired; build and retain the menu before any startup work that can block or prompt, and keep a secondary control surface for recovery.
- When extending gestures to the other hand, do not keep that hand locked to a single role; define how click/drag and scroll modes switch by posture so features do not silently conflict.
- On macOS capture permissions, do not assume the terminal app is the TCC target; surface the actual current process and bundle id, because Homebrew/venv Python may need permission separately from iTerm2.
- When a user says a regression started after a specific change set, rollback to the last known good revision first instead of layering more architecture on top of the broken path.
- Distinguish the visible pointer from the actual hit-test cursor; when the user wants a body-part overlay pointer, hide the system cursor and keep the overlay in sync instead of removing coordinate updates entirely.
- When a user says a trigger is too noisy and asks to remove it, take that trigger path out completely instead of trying to retune thresholds or keep a partial version alive.
