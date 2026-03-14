from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock, Timer, current_thread, main_thread

from ui_control_gesture.app.types import CaptionAnchor, CursorPoint, HandFeedback, Handedness, TranscriptResult

HAND_CONNECTIONS: tuple[tuple[int, int], ...] = (
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),
    (5, 9),
    (9, 10),
    (10, 11),
    (11, 12),
    (9, 13),
    (13, 14),
    (14, 15),
    (15, 16),
    (13, 17),
    (17, 18),
    (18, 19),
    (19, 20),
    (0, 17),
)


def _load_appkit():
    try:
        import AppKit
    except ImportError:  # pragma: no cover - runtime only
        return None
    return AppKit


@dataclass(slots=True)
class OverlayState:
    hand_feedback: list[HandFeedback] = field(default_factory=list)
    transcript: TranscriptResult | None = None


class OverlayRenderer:
    def __init__(self) -> None:
        self._appkit = _load_appkit()
        self._state = OverlayState()
        self._lock = Lock()

    def show_hand_feedback(self, feedback: HandFeedback | list[HandFeedback] | None) -> None:
        normalized = _normalize_feedback(feedback)
        with self._lock:
            self._state.hand_feedback = normalized
        if self._appkit is not None:  # pragma: no cover - runtime only
            self._request_render()

    def show_transcript(self, transcript: TranscriptResult, ttl_seconds: float) -> None:
        with self._lock:
            self._state.transcript = transcript
        if self._appkit is not None:  # pragma: no cover - runtime only
            self._request_render()
        Timer(ttl_seconds, self.clear_transcript).start()

    def clear_transcript(self) -> None:
        with self._lock:
            self._state.transcript = None
        if self._appkit is not None:  # pragma: no cover - runtime only
            self._request_render()

    def current_state(self) -> OverlayState:
        with self._lock:
            return OverlayState(
                hand_feedback=list(self._state.hand_feedback),
                transcript=self._state.transcript,
            )

    def _render(self) -> None:  # pragma: no cover - runtime only
        return None

    def _request_render(self) -> None:  # pragma: no cover - runtime only
        self._render()

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
        self._canvas = None
        self._render_bridge = None
        if self._appkit is not None:  # pragma: no cover - runtime only
            self._render_bridge = _build_main_thread_bridge(self._render)
            self._build_window()

    def _request_render(self) -> None:  # pragma: no cover - runtime only
        if current_thread() is main_thread():
            self._render()
            return
        if self._render_bridge is None:
            return
        self._render_bridge.performSelectorOnMainThread_withObject_waitUntilDone_("invoke:", None, False)

    def _build_window(self) -> None:  # pragma: no cover - runtime only
        appkit = self._appkit
        if appkit is None:
            return
        screen = appkit.NSScreen.mainScreen()
        if screen is None:
            return
        frame = screen.frame()
        frame_rect = ((frame.origin.x, frame.origin.y), (frame.size.width, frame.size.height))
        panel_class = _build_overlay_panel_class(appkit)
        style_mask = appkit.NSWindowStyleMaskBorderless | getattr(appkit, "NSWindowStyleMaskNonactivatingPanel", 0)
        window = panel_class.alloc().initWithContentRect_styleMask_backing_defer_(
            frame_rect,
            style_mask,
            appkit.NSBackingStoreBuffered,
            False,
        )
        window.setOpaque_(False)
        window.setBackgroundColor_(appkit.NSColor.clearColor())
        window.setIgnoresMouseEvents_(True)
        window.setHasShadow_(False)
        window.setHidesOnDeactivate_(False)
        window.setFloatingPanel_(True)
        window.setLevel_(appkit.NSFloatingWindowLevel)
        window.setCollectionBehavior_(
            appkit.NSWindowCollectionBehaviorCanJoinAllSpaces
            | getattr(appkit, "NSWindowCollectionBehaviorFullScreenAuxiliary", 0)
        )

        canvas = _build_overlay_canvas(self, frame_rect)
        window.setContentView_(canvas)
        window.orderFrontRegardless()

        self._window = window
        self._canvas = canvas
        self._render()

    def _render(self) -> None:  # pragma: no cover - runtime only
        appkit = self._appkit
        if appkit is None or self._window is None or self._canvas is None:
            return

        state = self.current_state()
        if not state.hand_feedback and state.transcript is None:
            self._window.orderOut_(None)
            return

        screen = appkit.NSScreen.mainScreen()
        if screen is None:
            return
        frame = screen.frame()
        frame_rect = ((frame.origin.x, frame.origin.y), (frame.size.width, frame.size.height))
        self._window.setFrame_display_(frame_rect, False)
        self._canvas.setFrame_(((0.0, 0.0), (frame.size.width, frame.size.height)))
        self._canvas.updateState_(state)
        self._window.orderFrontRegardless()


def _normalize_feedback(feedback: HandFeedback | list[HandFeedback] | None) -> list[HandFeedback]:
    if feedback is None:
        return []
    if isinstance(feedback, list):
        return list(feedback)
    return [feedback]


def _build_overlay_panel_class(appkit):  # pragma: no cover - runtime only
    from objc import super as objc_super

    class _OverlayPanel(appkit.NSPanel):
        def canBecomeKeyWindow(self):
            return False

        def canBecomeMainWindow(self):
            return False

        def initWithContentRect_styleMask_backing_defer_(self, rect, style_mask, backing, defer):
            self = objc_super(_OverlayPanel, self).initWithContentRect_styleMask_backing_defer_(
                rect,
                style_mask,
                backing,
                defer,
            )
            if self is None:
                return None
            self.setBecomesKeyOnlyIfNeeded_(False)
            return self

    return _OverlayPanel


def _build_overlay_canvas(renderer: AppKitOverlayWindow, frame_rect):  # pragma: no cover - runtime only
    appkit = renderer._appkit
    if appkit is None:
        return None

    from Foundation import NSString
    from objc import super as objc_super

    class _OverlayCanvas(appkit.NSView):
        def initWithFrame_renderer_(self, frame, bound_renderer):
            self = objc_super(_OverlayCanvas, self).initWithFrame_(frame)
            if self is None:
                return None
            self._renderer = bound_renderer
            self._state = OverlayState()
            return self

        def isOpaque(self):
            return False

        def updateState_(self, state: OverlayState) -> None:
            self._state = state
            self.setNeedsDisplay_(True)

        def drawRect_(self, dirty_rect) -> None:
            appkit.NSColor.clearColor().set()
            appkit.NSRectFill(dirty_rect)

            bounds = self.bounds()
            width = bounds.size.width
            height = bounds.size.height

            for hand_feedback in self._state.hand_feedback:
                _draw_hand_feedback(appkit, NSString, hand_feedback, height)

            if self._state.transcript is not None:
                _draw_transcript(appkit, NSString, self._state.transcript, width=width, height=height)

    return _OverlayCanvas.alloc().initWithFrame_renderer_(frame_rect, renderer)


def _draw_hand_feedback(appkit, ns_string_class, feedback: HandFeedback, screen_height: float) -> None:  # pragma: no cover - runtime only
    if feedback.skeleton_points:
        stroke_color = (
            appkit.NSColor.systemCyanColor()
            if feedback.handedness is Handedness.RIGHT
            else appkit.NSColor.systemGreenColor()
        )
        fill_color = (
            appkit.NSColor.systemBlueColor()
            if feedback.handedness is Handedness.RIGHT
            else appkit.NSColor.systemYellowColor()
        )
        stroke_color.setStroke()
        for start_index, end_index in HAND_CONNECTIONS:
            if start_index >= len(feedback.skeleton_points) or end_index >= len(feedback.skeleton_points):
                continue
            start = _to_appkit_point(feedback.skeleton_points[start_index], screen_height)
            end = _to_appkit_point(feedback.skeleton_points[end_index], screen_height)
            path = appkit.NSBezierPath.bezierPath()
            path.setLineWidth_(5.0)
            path.moveToPoint_(start)
            path.lineToPoint_(end)
            path.stroke()
        fill_color.setFill()
        for point in feedback.skeleton_points:
            appkit_point = _to_appkit_point(point, screen_height)
            oval_rect = ((appkit_point[0] - 5.0, appkit_point[1] - 5.0), (10.0, 10.0))
            appkit.NSBezierPath.bezierPathWithOvalInRect_(oval_rect).fill()

    if feedback.cursor is not None:
        label_origin = _to_appkit_point(feedback.cursor, screen_height)
        _draw_text(
            appkit,
            ns_string_class,
            f"{feedback.handedness.value}: {feedback.state_label}",
            (label_origin[0] + 18.0, label_origin[1] + 18.0),
            font_size=18.0,
            color=appkit.NSColor.whiteColor(),
        )


def _draw_transcript(appkit, ns_string_class, transcript: TranscriptResult, *, width: float, height: float) -> None:  # pragma: no cover - runtime only
    target = anchor_to_screen_position(transcript.anchor, transcript.cursor, width=width, height=height)
    appkit_point = _to_appkit_point(target, height)
    text_rect = ((max(16.0, appkit_point[0] - 280.0), max(16.0, appkit_point[1] - 36.0)), (560.0, 72.0))
    background = appkit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(text_rect, 18.0, 18.0)
    appkit.NSColor.colorWithCalibratedWhite_alpha_(0.08, 0.86).setFill()
    background.fill()
    _draw_text(
        appkit,
        ns_string_class,
        transcript.text,
        (text_rect[0][0] + 16.0, text_rect[0][1] + 20.0),
        font_size=24.0,
        color=appkit.NSColor.whiteColor(),
    )


def _draw_text(appkit, ns_string_class, text: str, point, *, font_size: float, color) -> None:  # pragma: no cover - runtime only
    font = None
    if hasattr(appkit.NSFont, "monospacedSystemFontOfSize_weight_"):
        font = appkit.NSFont.monospacedSystemFontOfSize_weight_(font_size, getattr(appkit, "NSFontWeightSemibold", 0.6))
    if font is None:
        font = appkit.NSFont.boldSystemFontOfSize_(font_size)
    attributes = {
        appkit.NSFontAttributeName: font,
        appkit.NSForegroundColorAttributeName: color,
    }
    ns_string_class.stringWithString_(text).drawAtPoint_withAttributes_(point, attributes)


def _to_appkit_point(point: CursorPoint, screen_height: float) -> tuple[float, float]:
    return point.x, screen_height - point.y


def _build_main_thread_bridge(callback):  # pragma: no cover - runtime only
    try:
        from Foundation import NSObject
        from objc import super as objc_super
    except ImportError:
        return None

    class _MainThreadBridge(NSObject):
        def initWithCallback_(self, bound_callback):
            self = objc_super(_MainThreadBridge, self).init()
            if self is None:
                return None
            self._callback = bound_callback
            return self

        def invoke_(self, _sender) -> None:
            self._callback()

    return _MainThreadBridge.alloc().initWithCallback_(callback)
