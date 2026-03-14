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
        feedback = self._feedback_from_hand(hand, cursor=cursor, state_label=state_label)
        return actions, feedback

    def _cursor_from_hand(self, hand: HandObservation) -> CursorPoint:
        x = ((1.0 - hand.palm_x) * self._screen_size.width) - (hand.palm_roll * self._config.roll_micro_adjust_gain)
        y = hand.palm_y * self._screen_size.height
        x = min(max(x, 0.0), self._screen_size.width - 1.0)
        y = min(max(y, 0.0), self._screen_size.height - 1.0)
        return CursorPoint(x=x, y=y)

    def _feedback_from_hand(self, hand: HandObservation, *, cursor: CursorPoint, state_label: str) -> HandFeedback:
        return HandFeedback(
            handedness=hand.handedness,
            cursor=cursor,
            state_label=state_label,
            skeleton_points=_project_skeleton(hand, self._screen_size),
        )


class SecondaryHandMapper:
    def __init__(self, config: GestureConfig, screen_size: ScreenSize) -> None:
        self._config = config
        self._screen_size = screen_size

    def map(self, hand: HandObservation) -> tuple[list[GestureAction], HandFeedback]:
        state_label = "ready"
        if abs(hand.middle_swipe_velocity_y) < self._config.scroll_deadzone:
            return [], self._feedback_from_hand(hand, state_label=state_label)
        state_label = "scroll"
        return [
            GestureAction(
                kind=GestureActionType.SCROLL,
                handedness=hand.handedness,
                scroll=ScrollDelta(dy=hand.middle_swipe_velocity_y),
            )
        ], self._feedback_from_hand(hand, state_label=state_label)

    def _feedback_from_hand(self, hand: HandObservation, *, state_label: str) -> HandFeedback:
        anchor = _project_point(hand.palm_x, hand.palm_y, self._screen_size)
        return HandFeedback(
            handedness=hand.handedness,
            cursor=anchor,
            state_label=state_label,
            skeleton_points=_project_skeleton(hand, self._screen_size),
        )


class HandGestureMapper:
    def __init__(self, config: GestureConfig) -> None:
        self._config = config
        self._primary: PrimaryHandMapper | None = None
        self._secondary: SecondaryHandMapper | None = None
        self._screen_size: ScreenSize | None = None

    def map(self, hands: list[HandObservation], screen_width: float, screen_height: float) -> tuple[list[GestureAction], list[HandFeedback]]:
        screen_size = ScreenSize(width=screen_width, height=screen_height)
        if self._primary is None or self._screen_size != screen_size:
            self._primary = PrimaryHandMapper(self._config, screen_size)
            self._secondary = SecondaryHandMapper(self._config, screen_size)
            self._screen_size = screen_size

        actions: list[GestureAction] = []
        feedback: list[HandFeedback] = []
        for hand in hands:
            if hand.handedness is Handedness.RIGHT:
                mapped_actions, hand_feedback = self._primary.map(hand)
                actions.extend(mapped_actions)
                feedback.append(hand_feedback)
            elif hand.handedness is Handedness.LEFT and self._secondary is not None:
                mapped_actions, hand_feedback = self._secondary.map(hand)
                actions.extend(mapped_actions)
                feedback.append(hand_feedback)
        return actions, feedback


def _project_point(x: float, y: float, screen_size: ScreenSize) -> CursorPoint:
    projected_x = min(max((1.0 - x) * screen_size.width, 0.0), screen_size.width - 1.0)
    projected_y = min(max(y * screen_size.height, 0.0), screen_size.height - 1.0)
    return CursorPoint(x=projected_x, y=projected_y)


def _project_skeleton(hand: HandObservation, screen_size: ScreenSize) -> tuple[CursorPoint, ...]:
    return tuple(_project_point(point.x, point.y, screen_size) for point in hand.landmarks)
