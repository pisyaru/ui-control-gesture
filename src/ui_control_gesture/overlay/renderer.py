from __future__ import annotations

from dataclasses import dataclass
from threading import Lock, Timer

from ui_control_gesture.app.types import CaptionAnchor, CursorPoint, HandFeedback, TranscriptResult


def _load_appkit():
    try:
        import AppKit
    except ImportError:  # pragma: no cover - runtime only
        return None
    return AppKit


@dataclass(slots=True)
class OverlayState:
    hand_feedback: HandFeedback | None = None
    transcript: TranscriptResult | None = None


class OverlayRenderer:
    def __init__(self) -> None:
        self._appkit = _load_appkit()
        self._state = OverlayState()
        self._lock = Lock()

    def show_hand_feedback(self, feedback: HandFeedback | list[HandFeedback] | None) -> None:
        primary_feedback = feedback
        if isinstance(feedback, list):
            primary_feedback = feedback[0] if feedback else None
        with self._lock:
            self._state.hand_feedback = primary_feedback
        if self._appkit is not None:  # pragma: no cover - runtime only
            self._render()

    def show_transcript(self, transcript: TranscriptResult, ttl_seconds: float) -> None:
        with self._lock:
            self._state.transcript = transcript
        if self._appkit is not None:  # pragma: no cover - runtime only
            self._render()
        Timer(ttl_seconds, self.clear_transcript).start()

    def clear_transcript(self) -> None:
        with self._lock:
            self._state.transcript = None
        if self._appkit is not None:  # pragma: no cover - runtime only
            self._render()

    def current_state(self) -> OverlayState:
        with self._lock:
            return OverlayState(
                hand_feedback=self._state.hand_feedback,
                transcript=self._state.transcript,
            )

    def _render(self) -> None:  # pragma: no cover - runtime only
        # Placeholder AppKit hook. The app shell reads `current_state()` and paints the floating labels.
        return None

    def show_caption(
        self,
        *,
        text: str,
        anchor: CaptionAnchor,
        cursor: CursorPoint | None,
        ttl_seconds: float,
    ) -> None:
        self.show_transcript(
            TranscriptResult(text=text, anchor=anchor, cursor=cursor),
            ttl_seconds=ttl_seconds,
        )


def anchor_to_screen_position(anchor: CaptionAnchor, cursor: CursorPoint | None, width: float, height: float) -> CursorPoint:
    if anchor == CaptionAnchor.CURSOR and cursor is not None:
        return cursor
    if anchor == CaptionAnchor.LEFT:
        return CursorPoint(x=width * 0.2, y=height * 0.5)
    if anchor == CaptionAnchor.RIGHT:
        return CursorPoint(x=width * 0.8, y=height * 0.5)
    if anchor == CaptionAnchor.UP:
        return CursorPoint(x=width * 0.5, y=height * 0.2)
    if anchor == CaptionAnchor.DOWN:
        return CursorPoint(x=width * 0.5, y=height * 0.8)
    return CursorPoint(x=width * 0.5, y=height * 0.5)


class AppKitOverlayWindow(OverlayRenderer):
    def __init__(self) -> None:
        super().__init__()
        self._window = None
        self._label = None
        if self._appkit is not None:  # pragma: no cover - runtime only
            self._build_window()

    def _build_window(self) -> None:  # pragma: no cover - runtime only
        appkit = self._appkit
        if appkit is None:
            return
        window = appkit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            ((0.0, 0.0), (420.0, 96.0)),
            appkit.NSWindowStyleMaskBorderless,
            appkit.NSBackingStoreBuffered,
            False,
        )
        window.setOpaque_(False)
        window.setBackgroundColor_(appkit.NSColor.clearColor())
        window.setIgnoresMouseEvents_(True)
        window.setLevel_(appkit.NSFloatingWindowLevel)
        window.setCollectionBehavior_(appkit.NSWindowCollectionBehaviorCanJoinAllSpaces)

        label = appkit.NSTextField.alloc().initWithFrame_(((12.0, 20.0), (396.0, 56.0)))
        label.setEditable_(False)
        label.setBordered_(False)
        label.setSelectable_(False)
        label.setDrawsBackground_(False)
        label.setTextColor_(appkit.NSColor.whiteColor())
        label.setFont_(appkit.NSFont.boldSystemFontOfSize_(20.0))
        label.setAlignment_(appkit.NSTextAlignmentCenter)

        content = appkit.NSView.alloc().initWithFrame_(((0.0, 0.0), (420.0, 96.0)))
        content.addSubview_(label)
        window.setContentView_(content)
        window.orderFrontRegardless()

        self._window = window
        self._label = label
        self._render()

    def _render(self) -> None:  # pragma: no cover - runtime only
        appkit = self._appkit
        if appkit is None or self._window is None or self._label is None:
            return
        state = self.current_state()
        screen = appkit.NSScreen.mainScreen()
        if screen is None:
            return
        frame = screen.visibleFrame()

        if state.transcript is not None:
            target = anchor_to_screen_position(
                state.transcript.anchor,
                state.transcript.cursor,
                width=frame.size.width,
                height=frame.size.height,
            )
            text = state.transcript.text
        elif state.hand_feedback is not None:
            target = state.hand_feedback.cursor
            text = f"\u270b {state.hand_feedback.handedness.value}: {state.hand_feedback.state_label}"
        else:
            self._window.orderOut_(None)
            return

        self._label.setStringValue_(text)
        x = max(0.0, min(frame.size.width - 420.0, target.x - 210.0))
        y = max(0.0, min(frame.size.height - 96.0, frame.size.height - target.y))
        self._window.setFrameOrigin_((x, y))
        self._window.orderFrontRegardless()
