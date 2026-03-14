import unittest
from unittest.mock import Mock, patch

from ui_control_gesture.app.types import CaptionAnchor, CursorPoint, HandFeedback, Handedness, TranscriptResult
from ui_control_gesture.overlay.renderer import OverlayRenderer


class _RecordingOverlayRenderer(OverlayRenderer):
    def __init__(self) -> None:
        super().__init__()
        self._appkit = object()
        self.request_render_calls = 0
        self.render_calls = 0

    def _request_render(self) -> None:
        self.request_render_calls += 1

    def _render(self) -> None:
        self.render_calls += 1


class OverlayRendererTests(unittest.TestCase):
    def test_hand_feedback_uses_request_render_path(self) -> None:
        renderer = _RecordingOverlayRenderer()

        renderer.show_hand_feedback(
            HandFeedback(
                handedness=Handedness.RIGHT,
                cursor=CursorPoint(x=100, y=120),
                state_label="move",
            )
        )

        self.assertEqual(renderer.request_render_calls, 1)
        self.assertEqual(renderer.render_calls, 0)

    def test_hand_feedback_accepts_multiple_skeletons(self) -> None:
        renderer = _RecordingOverlayRenderer()

        renderer.show_hand_feedback(
            [
                HandFeedback(
                    handedness=Handedness.RIGHT,
                    cursor=CursorPoint(x=100, y=120),
                    state_label="move",
                    skeleton_points=(CursorPoint(x=100, y=120),),
                ),
                HandFeedback(
                    handedness=Handedness.LEFT,
                    cursor=CursorPoint(x=220, y=240),
                    state_label="scroll",
                    skeleton_points=(CursorPoint(x=220, y=240),),
                ),
            ]
        )

        state = renderer.current_state()
        self.assertEqual(len(state.hand_feedback), 2)
        self.assertEqual(renderer.request_render_calls, 1)

    @patch("ui_control_gesture.overlay.renderer.Timer")
    def test_transcript_clear_uses_request_render_path(self, timer_mock: Mock) -> None:
        renderer = _RecordingOverlayRenderer()

        renderer.show_transcript(
            TranscriptResult(text="hello", anchor=CaptionAnchor.CENTER, cursor=None),
            ttl_seconds=60.0,
        )
        renderer.clear_transcript()

        self.assertEqual(renderer.request_render_calls, 2)
        self.assertEqual(renderer.render_calls, 0)
        timer_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
