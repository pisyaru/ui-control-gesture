import unittest

from ui_control_gesture.app.config import GestureConfig
from ui_control_gesture.app.types import GestureActionType, HandObservation, Handedness, NormalizedPoint
from ui_control_gesture.gesture.hand_mapper import HandGestureMapper


def make_hand(
    handedness: Handedness,
    *,
    x: float = 0.5,
    y: float = 0.5,
    roll: float = 0.0,
    index_touch: bool = False,
    middle_touch: bool = False,
    fist: bool = False,
    swipe: float = 0.0,
    landmarks: tuple[NormalizedPoint, ...] = (),
) -> HandObservation:
    return HandObservation(
        handedness=handedness,
        palm_x=x,
        palm_y=y,
        palm_roll=roll,
        landmarks=landmarks,
        index_thumb_touching=index_touch,
        middle_thumb_touching=middle_touch,
        fist_closed=fist,
        middle_swipe_velocity_y=swipe,
        confidence=0.99,
    )


def action_kinds(actions):
    return [action.kind for action in actions]


class HandGestureMapperTests(unittest.TestCase):
    def test_short_index_pinch_becomes_left_click(self) -> None:
        mapper = HandGestureMapper(GestureConfig(drag_activation_frames=3))

        mapper.map([make_hand(Handedness.RIGHT, index_touch=True)], screen_width=1000, screen_height=800)
        actions, _ = mapper.map([make_hand(Handedness.RIGHT, index_touch=False)], screen_width=1000, screen_height=800)

        self.assertEqual(
            action_kinds(actions),
            [GestureActionType.MOVE_CURSOR, GestureActionType.LEFT_DOWN, GestureActionType.LEFT_UP],
        )

    def test_long_index_pinch_becomes_drag(self) -> None:
        mapper = HandGestureMapper(GestureConfig(drag_activation_frames=2))

        mapper.map([make_hand(Handedness.RIGHT, index_touch=True)], screen_width=1000, screen_height=800)
        actions, _ = mapper.map([make_hand(Handedness.RIGHT, index_touch=True)], screen_width=1000, screen_height=800)

        self.assertIn(GestureActionType.LEFT_DOWN, action_kinds(actions))

        release_actions, _ = mapper.map([make_hand(Handedness.RIGHT, index_touch=False)], screen_width=1000, screen_height=800)
        self.assertIn(GestureActionType.LEFT_UP, action_kinds(release_actions))

    def test_fist_starts_and_stops_stt(self) -> None:
        mapper = HandGestureMapper(GestureConfig())

        start_actions, _ = mapper.map([make_hand(Handedness.RIGHT, fist=True)], screen_width=1000, screen_height=800)
        stop_actions, _ = mapper.map([make_hand(Handedness.RIGHT, fist=False)], screen_width=1000, screen_height=800)

        self.assertIn(GestureActionType.START_FIST_STT, action_kinds(start_actions))
        self.assertIn(GestureActionType.STOP_FIST_STT, action_kinds(stop_actions))

    def test_left_hand_scroll_is_independent(self) -> None:
        mapper = HandGestureMapper(GestureConfig(scroll_deadzone=0.01))

        actions, _ = mapper.map(
            [
                make_hand(Handedness.RIGHT, index_touch=True),
                make_hand(Handedness.LEFT, swipe=0.4),
            ],
            screen_width=1000,
            screen_height=800,
        )

        self.assertIn(GestureActionType.SCROLL, action_kinds(actions))
        self.assertIn(GestureActionType.MOVE_CURSOR, action_kinds(actions))

    def test_roll_adjusts_cursor_x(self) -> None:
        mapper = HandGestureMapper(GestureConfig(roll_micro_adjust_gain=40.0))
        base_actions, _ = mapper.map([make_hand(Handedness.RIGHT, roll=0.0)], screen_width=1000, screen_height=800)
        rolled_actions, _ = mapper.map([make_hand(Handedness.RIGHT, roll=0.5)], screen_width=1000, screen_height=800)

        base_cursor = next(action.cursor for action in base_actions if action.kind == GestureActionType.MOVE_CURSOR)
        rolled_cursor = next(action.cursor for action in rolled_actions if action.kind == GestureActionType.MOVE_CURSOR)

        self.assertIsNotNone(rolled_cursor)
        self.assertIsNotNone(base_cursor)
        self.assertLess(rolled_cursor.x, base_cursor.x)

    def test_cursor_x_is_mirrored_from_camera_space(self) -> None:
        mapper = HandGestureMapper(GestureConfig())
        left_camera_actions, _ = mapper.map([make_hand(Handedness.RIGHT, x=0.2)], screen_width=1000, screen_height=800)
        right_camera_actions, _ = mapper.map([make_hand(Handedness.RIGHT, x=0.8)], screen_width=1000, screen_height=800)

        left_camera_cursor = next(action.cursor for action in left_camera_actions if action.kind == GestureActionType.MOVE_CURSOR)
        right_camera_cursor = next(action.cursor for action in right_camera_actions if action.kind == GestureActionType.MOVE_CURSOR)

        self.assertGreater(left_camera_cursor.x, right_camera_cursor.x)

    def test_feedback_contains_both_hands_and_mirrored_skeleton(self) -> None:
        mapper = HandGestureMapper(GestureConfig(scroll_deadzone=0.01))
        actions, feedback = mapper.map(
            [
                make_hand(
                    Handedness.RIGHT,
                    landmarks=(NormalizedPoint(x=0.2, y=0.3), NormalizedPoint(x=0.4, y=0.5)),
                ),
                make_hand(
                    Handedness.LEFT,
                    swipe=0.2,
                    landmarks=(NormalizedPoint(x=0.8, y=0.25), NormalizedPoint(x=0.75, y=0.35)),
                ),
            ],
            screen_width=1000,
            screen_height=800,
        )

        self.assertEqual(len(feedback), 2)
        self.assertIn(GestureActionType.SCROLL, action_kinds(actions))
        right_feedback = next(item for item in feedback if item.handedness is Handedness.RIGHT)
        left_feedback = next(item for item in feedback if item.handedness is Handedness.LEFT)
        self.assertAlmostEqual(right_feedback.skeleton_points[0].x, 800.0)
        self.assertAlmostEqual(left_feedback.skeleton_points[0].x, 200.0)


if __name__ == "__main__":
    unittest.main()
