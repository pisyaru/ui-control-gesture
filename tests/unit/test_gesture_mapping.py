import unittest

from ui_control_gesture.app.config import GestureConfig
from ui_control_gesture.app.types import GestureActionType, HandObservation, Handedness, HeadObservation, NormalizedPoint
from ui_control_gesture.gesture.hand_mapper import PrimaryHandMapper, SecondaryHandMapper
from ui_control_gesture.gesture.head_mapper import HeadAnchorMapper
from ui_control_gesture.system.macos_input import ScreenSize


class GestureMappingTests(unittest.TestCase):
    def test_primary_hand_emits_cursor_and_click_cycle(self) -> None:
        mapper = PrimaryHandMapper(GestureConfig(), ScreenSize(width=1000.0, height=800.0))
        hand = HandObservation(
            handedness=Handedness.RIGHT,
            palm_x=0.5,
            palm_y=0.5,
            palm_roll=0.0,
            landmarks=(NormalizedPoint(x=0.5, y=0.5),),
            index_thumb_touching=True,
        )
        actions, feedback = mapper.map(hand)
        self.assertEqual(
            [action.kind for action in actions],
            [GestureActionType.MOVE_CURSOR, GestureActionType.LEFT_DOWN],
        )
        self.assertEqual(feedback.state_label, "left-drag")

        released_actions, released_feedback = mapper.map(
            HandObservation(
                handedness=Handedness.RIGHT,
                palm_x=0.5,
                palm_y=0.5,
                palm_roll=0.0,
                landmarks=(NormalizedPoint(x=0.5, y=0.5),),
                index_thumb_touching=False,
            )
        )
        self.assertEqual(
            [action.kind for action in released_actions],
            [GestureActionType.MOVE_CURSOR, GestureActionType.LEFT_UP],
        )
        self.assertEqual(released_feedback.state_label, "left-release")

    def test_primary_hand_emits_fist_recording_transitions(self) -> None:
        mapper = PrimaryHandMapper(GestureConfig(), ScreenSize(width=1000.0, height=800.0))
        start_actions, _ = mapper.map(
            HandObservation(
                handedness=Handedness.RIGHT,
                palm_x=0.5,
                palm_y=0.5,
                palm_roll=0.0,
                landmarks=(NormalizedPoint(x=0.5, y=0.5),),
                fist_closed=True,
            )
        )
        self.assertEqual(
            [action.kind for action in start_actions],
            [GestureActionType.MOVE_CURSOR, GestureActionType.START_FIST_STT],
        )

        stop_actions, _ = mapper.map(
            HandObservation(
                handedness=Handedness.RIGHT,
                palm_x=0.5,
                palm_y=0.5,
                palm_roll=0.0,
                landmarks=(NormalizedPoint(x=0.5, y=0.5),),
                fist_closed=False,
            )
        )
        self.assertEqual(
            [action.kind for action in stop_actions],
            [GestureActionType.MOVE_CURSOR, GestureActionType.STOP_FIST_STT],
        )

    def test_secondary_hand_maps_middle_swipe_to_scroll(self) -> None:
        mapper = SecondaryHandMapper(GestureConfig(scroll_deadzone=0.02), ScreenSize(width=1000.0, height=800.0))
        actions, feedback = mapper.map(
            HandObservation(
                handedness=Handedness.LEFT,
                palm_x=0.25,
                palm_y=0.3,
                palm_roll=0.0,
                landmarks=(NormalizedPoint(x=0.25, y=0.3),),
                middle_swipe_velocity_y=0.2,
            )
        )
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].kind, GestureActionType.SCROLL)
        self.assertEqual(feedback.state_label, "scroll")

    def test_head_anchor_mapper_uses_five_zones(self) -> None:
        mapper = HeadAnchorMapper(yaw_threshold=0.05, pitch_threshold=0.05)
        self.assertEqual(mapper.map(None).value, "center")
        self.assertEqual(mapper.map(HeadObservation(yaw=-0.1, pitch=0.0)).value, "left")
        self.assertEqual(mapper.map(HeadObservation(yaw=0.1, pitch=0.0)).value, "right")
        self.assertEqual(mapper.map(HeadObservation(yaw=0.0, pitch=-0.1)).value, "up")
        self.assertEqual(mapper.map(HeadObservation(yaw=0.0, pitch=0.1)).value, "down")


if __name__ == "__main__":
    unittest.main()
