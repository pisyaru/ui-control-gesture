import unittest

from ui_control_gesture.app.types import CaptionAnchor, HeadObservation
from ui_control_gesture.gesture.head_mapper import HeadCaptionAnchorMapper


class HeadCaptionAnchorMapperTests(unittest.TestCase):
    def test_head_anchor_defaults_to_center(self) -> None:
        mapper = HeadCaptionAnchorMapper()
        self.assertEqual(mapper.map(None), CaptionAnchor.CENTER)

    def test_head_anchor_maps_yaw_and_pitch(self) -> None:
        mapper = HeadCaptionAnchorMapper(yaw_threshold=0.1, pitch_threshold=0.1)

        self.assertEqual(mapper.map(HeadObservation(yaw=0.15, pitch=0.0)), CaptionAnchor.RIGHT)
        self.assertEqual(mapper.map(HeadObservation(yaw=-0.15, pitch=0.0)), CaptionAnchor.LEFT)
        self.assertEqual(mapper.map(HeadObservation(yaw=0.0, pitch=-0.12)), CaptionAnchor.UP)
        self.assertEqual(mapper.map(HeadObservation(yaw=0.0, pitch=0.15)), CaptionAnchor.DOWN)


if __name__ == "__main__":
    unittest.main()
