from __future__ import annotations

from dataclasses import dataclass, field

from ui_control_gesture.app.config import GestureConfig
from ui_control_gesture.app.types import (
    CursorPoint,
    GestureAction,
    GestureActionType,
    HandFeedback,
    HandObservation,
    Handedness,
    ScrollDelta,
)
from ui_control_gesture.system.macos_input import ScreenSize


@dataclass(slots=True)
class PrimaryHandState:
    left_active: bool = False
    right_active: bool = False
    left_pinch_frames: int = 0
    right_pinch_frames: int = 0
    fist_active: bool = False
    last_cursor: CursorPoint = field(default_factory=lambda: CursorPoint(x=0.0, y=0.0))


class PrimaryHandMapper:
    def __init__(self, config: GestureConfig, screen_size: ScreenSize) -> None:
        self._config = config
        self._screen_size = screen_size
        self._state = PrimaryHandState()

    def map(self, hand: HandObservation) -> tuple[list[GestureAction], HandFeedback]:
        cursor = self._cursor_from_hand(hand)
        actions = [GestureAction(kind=GestureActionType.MOVE_CURSOR, handedness=hand.handedness, cursor=cursor)]
        state_label = "move"

        if hand.fist_closed and not self._state.fist_active and not self._state.left_active and not self._state.right_active:
            self._state.fist_active = True
            self._state.left_pinch_frames = 0
            self._state.right_pinch_frames = 0
            actions.append(GestureAction(kind=GestureActionType.START_FIST_STT, handedness=hand.handedness, cursor=cursor))
            state_label = "fist-record"
        elif not hand.fist_closed and self._state.fist_active:
            self._state.fist_active = False
            actions.append(GestureAction(kind=GestureActionType.STOP_FIST_STT, handedness=hand.handedness, cursor=cursor))
            state_label = "fist-release"
        elif hand.index_thumb_touching and not hand.middle_thumb_touching and not self._state.fist_active:
            self._state.left_pinch_frames += 1
            if not self._state.left_active and self._state.left_pinch_frames >= self._config.drag_activation_frames:
                actions.append(GestureAction(kind=GestureActionType.LEFT_DOWN, handedness=hand.handedness, cursor=cursor))
                self._state.left_active = True
            state_label = "left-drag" if self._state.left_active else "left-pinch"
        elif self._state.left_active or self._state.left_pinch_frames:
            if self._state.left_active:
                actions.append(GestureAction(kind=GestureActionType.LEFT_UP, handedness=hand.handedness, cursor=cursor))
                self._state.left_active = False
                state_label = "left-release"
            elif 0 < self._state.left_pinch_frames < self._config.drag_activation_frames:
                actions.append(GestureAction(kind=GestureActionType.LEFT_DOWN, handedness=hand.handedness, cursor=cursor))
                actions.append(GestureAction(kind=GestureActionType.LEFT_UP, handedness=hand.handedness, cursor=cursor))
                state_label = "left-click"
            self._state.left_pinch_frames = 0
        elif hand.middle_thumb_touching and not hand.index_thumb_touching and not self._state.fist_active:
            self._state.right_pinch_frames += 1
            if not self._state.right_active and self._state.right_pinch_frames >= self._config.drag_activation_frames:
                actions.append(GestureAction(kind=GestureActionType.RIGHT_DOWN, handedness=hand.handedness, cursor=cursor))
                self._state.right_active = True
            state_label = "right-drag" if self._state.right_active else "right-pinch"
        elif self._state.right_active or self._state.right_pinch_frames:
            if self._state.right_active:
                actions.append(GestureAction(kind=GestureActionType.RIGHT_UP, handedness=hand.handedness, cursor=cursor))
                self._state.right_active = False
                state_label = "right-release"
            elif 0 < self._state.right_pinch_frames < self._config.drag_activation_frames:
                actions.append(GestureAction(kind=GestureActionType.RIGHT_DOWN, handedness=hand.handedness, cursor=cursor))
                actions.append(GestureAction(kind=GestureActionType.RIGHT_UP, handedness=hand.handedness, cursor=cursor))
                state_label = "right-click"
            self._state.right_pinch_frames = 0

        self._state.last_cursor = cursor
        feedback = HandFeedback(handedness=hand.handedness, cursor=cursor, state_label=state_label)
        return actions, feedback

    def _cursor_from_hand(self, hand: HandObservation) -> CursorPoint:
        x = hand.palm_x * self._screen_size.width + (hand.palm_roll * self._config.roll_micro_adjust_gain)
        y = hand.palm_y * self._screen_size.height
        x = min(max(x, 0.0), self._screen_size.width - 1.0)
        y = min(max(y, 0.0), self._screen_size.height - 1.0)
        return CursorPoint(x=x, y=y)


class SecondaryHandMapper:
    def __init__(self, config: GestureConfig) -> None:
        self._config = config

    def map(self, hand: HandObservation) -> list[GestureAction]:
        if abs(hand.middle_swipe_velocity_y) < self._config.scroll_deadzone:
            return []
        return [
            GestureAction(
                kind=GestureActionType.SCROLL,
                handedness=hand.handedness,
                scroll=ScrollDelta(dy=hand.middle_swipe_velocity_y),
            )
        ]


class HandGestureMapper:
    def __init__(self, config: GestureConfig) -> None:
        self._config = config
        self._primary: PrimaryHandMapper | None = None
        self._secondary = SecondaryHandMapper(config)
        self._screen_size: ScreenSize | None = None

    def map(self, hands: list[HandObservation], screen_width: float, screen_height: float) -> tuple[list[GestureAction], list[HandFeedback]]:
        screen_size = ScreenSize(width=screen_width, height=screen_height)
        if self._primary is None or self._screen_size != screen_size:
            self._primary = PrimaryHandMapper(self._config, screen_size)
            self._screen_size = screen_size

        actions: list[GestureAction] = []
        feedback: list[HandFeedback] = []
        for hand in hands:
            if hand.handedness is Handedness.RIGHT:
                mapped_actions, hand_feedback = self._primary.map(hand)
                actions.extend(mapped_actions)
                feedback.append(hand_feedback)
            elif hand.handedness is Handedness.LEFT:
                actions.extend(self._secondary.map(hand))
        return actions, feedback
