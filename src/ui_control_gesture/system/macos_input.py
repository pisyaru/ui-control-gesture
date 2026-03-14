from __future__ import annotations

from dataclasses import dataclass
from math import copysign

from ui_control_gesture.app.types import CursorPoint, GestureAction, GestureActionType


def _load_quartz():
    try:
        import Quartz
    except ImportError:  # pragma: no cover - import depends on runtime
        return None
    return Quartz


@dataclass(slots=True)
class ScreenSize:
    width: float
    height: float


@dataclass(slots=True)
class ScreenFrame(ScreenSize):
    pass


class MacOSInputController:
    def __init__(self) -> None:
        self._quartz = _load_quartz()
        self._left_down = False
        self._right_down = False

    def screen_size(self) -> ScreenSize:
        if self._quartz is None:
            return ScreenSize(width=1440.0, height=900.0)
        main_id = self._quartz.CGMainDisplayID()
        return ScreenSize(
            width=float(self._quartz.CGDisplayPixelsWide(main_id)),
            height=float(self._quartz.CGDisplayPixelsHigh(main_id)),
        )

    def perform(self, action: GestureAction) -> None:
        if action.kind == GestureActionType.MOVE_CURSOR and action.cursor is not None:
            self.move_cursor(action.cursor)
            return
        if action.kind == GestureActionType.LEFT_DOWN and action.cursor is not None:
            self.left_down(action.cursor)
            return
        if action.kind == GestureActionType.LEFT_UP and action.cursor is not None:
            self.left_up(action.cursor)
            return
        if action.kind == GestureActionType.RIGHT_DOWN and action.cursor is not None:
            self.right_down(action.cursor)
            return
        if action.kind == GestureActionType.RIGHT_UP and action.cursor is not None:
            self.right_up(action.cursor)
            return
        if action.kind == GestureActionType.SCROLL and action.scroll is not None:
            self.scroll(action.scroll.dy)

    def move_cursor(self, cursor: CursorPoint) -> None:
        if self._quartz is None:  # pragma: no cover - runtime only
            return
        self._quartz.CGWarpMouseCursorPosition((cursor.x, cursor.y))
        if self._left_down:
            event_type = self._quartz.kCGEventLeftMouseDragged
        elif self._right_down:
            event_type = self._quartz.kCGEventRightMouseDragged
        else:
            event_type = self._quartz.kCGEventMouseMoved
        event = self._quartz.CGEventCreateMouseEvent(None, event_type, (cursor.x, cursor.y), 0)
        self._quartz.CGEventPost(self._quartz.kCGHIDEventTap, event)

    def left_down(self, cursor: CursorPoint) -> None:
        self._left_down = True
        self._post_mouse(self._quartz.kCGEventLeftMouseDown if self._quartz else None, cursor, 0)

    def left_up(self, cursor: CursorPoint) -> None:
        self._left_down = False
        self._post_mouse(self._quartz.kCGEventLeftMouseUp if self._quartz else None, cursor, 0)

    def right_down(self, cursor: CursorPoint) -> None:
        self._right_down = True
        self._post_mouse(self._quartz.kCGEventRightMouseDown if self._quartz else None, cursor, 1)

    def right_up(self, cursor: CursorPoint) -> None:
        self._right_down = False
        self._post_mouse(self._quartz.kCGEventRightMouseUp if self._quartz else None, cursor, 1)

    def scroll(self, delta_y: float) -> None:
        if self._quartz is None:  # pragma: no cover - runtime only
            return
        wheel_delta = int(copysign(max(1, abs(delta_y) * 16), -delta_y))
        event = self._quartz.CGEventCreateScrollWheelEvent(
            None,
            self._quartz.kCGScrollEventUnitLine,
            1,
            wheel_delta,
        )
        self._quartz.CGEventPost(self._quartz.kCGHIDEventTap, event)

    def _post_mouse(self, event_type: int | None, cursor: CursorPoint, button: int) -> None:
        if self._quartz is None or event_type is None:  # pragma: no cover - runtime only
            return
        event = self._quartz.CGEventCreateMouseEvent(None, event_type, (cursor.x, cursor.y), button)
        self._quartz.CGEventPost(self._quartz.kCGHIDEventTap, event)


class QuartzMacInputController(MacOSInputController):
    def screen_frame(self) -> ScreenFrame:
        screen = self.screen_size()
        return ScreenFrame(width=screen.width, height=screen.height)

    def press_left(self, cursor: CursorPoint) -> None:
        self.left_down(cursor)

    def release_left(self, cursor: CursorPoint) -> None:
        self.left_up(cursor)

    def press_right(self, cursor: CursorPoint) -> None:
        self.right_down(cursor)

    def release_right(self, cursor: CursorPoint) -> None:
        self.right_up(cursor)
