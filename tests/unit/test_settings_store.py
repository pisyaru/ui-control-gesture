import unittest

from ui_control_gesture.app.config import default_config
from ui_control_gesture.settings.store import SettingsStore


class SettingsStoreTests(unittest.TestCase):
    def test_settings_store_notifies_subscribers(self) -> None:
        store = SettingsStore(default_config())
        seen = []

        store.subscribe(lambda config: seen.append(config.toggles.hand_enabled))
        store.update_toggle(hand=False)

        self.assertEqual(seen, [False])

    def test_settings_store_updates_camera_index(self) -> None:
        store = SettingsStore(default_config())
        store.set_camera_index(2)
        self.assertEqual(store.config.camera_index, 2)


if __name__ == "__main__":
    unittest.main()
