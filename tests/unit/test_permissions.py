import unittest
from unittest.mock import Mock, patch

from ui_control_gesture.system.permissions import (
    PermissionState,
    open_privacy_settings,
    permission_summary_text,
    prompt_for_permissions,
    query_permission_state,
)


class _FakeCaptureDevice:
    @staticmethod
    def authorizationStatusForMediaType_(media_type):
        return {"video": 2, "audio": 3}[media_type]


class PermissionTests(unittest.TestCase):
    def test_permission_summary_mentions_denied_camera_recovery(self) -> None:
        state = PermissionState(
            camera=False,
            camera_status="denied",
            microphone=True,
            microphone_status="authorized",
            accessibility=True,
            input_monitoring=False,
        )

        summary = permission_summary_text(state)

        self.assertIn("camera: denied", summary)
        self.assertIn("Privacy & Security > Camera", summary)
        self.assertIn("allow the terminal app or Python", summary)

    def test_permission_summary_mentions_pending_camera_recovery(self) -> None:
        state = PermissionState(
            camera=False,
            camera_status="not_determined",
            microphone=False,
            microphone_status="not_determined",
            accessibility=True,
            input_monitoring=True,
        )

        summary = permission_summary_text(state)

        self.assertIn("camera access is still pending", summary)
        self.assertIn("microphone access is still pending", summary)

    @patch("ui_control_gesture.system.permissions._load_capture_symbols")
    @patch("ui_control_gesture.system.permissions._load_input_monitoring_symbols")
    @patch("ui_control_gesture.system.permissions._load_accessibility_symbols")
    def test_query_permission_state_keeps_capture_status_when_accessibility_symbols_are_missing(
        self,
        accessibility_mock: Mock,
        input_monitoring_mock: Mock,
        capture_mock: Mock,
    ) -> None:
        accessibility_mock.return_value = None
        input_monitoring_mock.return_value = (lambda: False, lambda: False)
        capture_mock.return_value = (_FakeCaptureDevice, "audio", "video")

        state = query_permission_state()

        self.assertFalse(state.camera)
        self.assertEqual(state.camera_status, "denied")
        self.assertTrue(state.microphone)
        self.assertEqual(state.microphone_status, "authorized")
        self.assertFalse(state.accessibility)
        self.assertFalse(state.input_monitoring)

    @patch("ui_control_gesture.system.permissions._request_capture_access")
    @patch("ui_control_gesture.system.permissions._query_capture_authorization")
    @patch("ui_control_gesture.system.permissions._load_capture_symbols")
    @patch("ui_control_gesture.system.permissions._request_permission_status")
    def test_prompt_for_permissions_uses_capture_symbols_even_without_accessibility_module(
        self,
        request_status_mock: Mock,
        capture_symbols_mock: Mock,
        query_capture_mock: Mock,
        request_capture_mock: Mock,
    ) -> None:
        request_status_mock.return_value.accessibility_trusted = False
        request_status_mock.return_value.input_monitoring_trusted = False
        capture_symbols_mock.return_value = (_FakeCaptureDevice, "audio", "video")
        request_capture_mock.side_effect = [False, True]
        query_capture_mock.return_value = ((False, "denied"), (True, "authorized"))

        state = prompt_for_permissions()

        self.assertEqual(state.camera_status, "denied")
        self.assertEqual(state.microphone_status, "authorized")

    @patch("ui_control_gesture.system.permissions.subprocess.run")
    def test_open_privacy_settings_uses_expected_url(self, run_mock: Mock) -> None:
        run_mock.return_value.returncode = 0

        result = open_privacy_settings("camera")

        self.assertTrue(result)
        run_mock.assert_called_once_with(
            ["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Camera"],
            check=False,
            capture_output=True,
        )


if __name__ == "__main__":
    unittest.main()
