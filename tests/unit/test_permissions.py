import unittest
from unittest.mock import Mock, patch

from ui_control_gesture.system.permissions import PermissionState, open_privacy_settings, permission_summary_text


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
