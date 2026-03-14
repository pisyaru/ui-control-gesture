from __future__ import annotations

import signal
from typing import Callable


def run_menu_bar_app(factory: Callable[[], object]) -> None:
    try:
        from AppKit import (
            NSApp,
            NSApplication,
            NSApplicationActivationPolicyAccessory,
            NSControlStateValueOff,
            NSControlStateValueOn,
            NSMenu,
            NSMenuItem,
            NSStatusBar,
        )
        from Foundation import NSObject, NSTimer
        from objc import super as objc_super
    except Exception as exc:  # pragma: no cover - macOS-only path
        raise RuntimeError("PyObjC AppKit is required to run the menu bar app.") from exc

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    app_controller = factory()
    stt_models = (
        ("Voxtral Realtime", "mistralai/Voxtral-Mini-4B-Realtime-2602"),
        ("Qwen3-ASR 1.7B 8bit", "mlx-community/Qwen3-ASR-1.7B-8bit"),
        ("Qwen3-ASR 0.6B 4bit", "mlx-community/Qwen3-ASR-0.6B-4bit"),
    )
    tts_models = (
        ("Qwen3-TTS 0.6B Base", "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-8bit"),
        ("Qwen3-TTS 1.7B VoiceDesign", "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit"),
        ("Fish Speech S2 Pro", "fishaudio/s2-pro"),
    )

    class AppDelegate(NSObject):  # pragma: no cover - UI wiring
        def init(self):
            self = objc_super(AppDelegate, self).init()
            if self is None:
                return None
            self.controller = app_controller
            self.status_item = None
            self.hand_item = None
            self.head_item = None
            self.stt_item = None
            self.tts_item = None
            self.stt_model_items = {}
            self.tts_model_items = {}
            self.camera_items = {}
            self.camera_root_item = None
            self.signal_timer = None
            return self

        def applicationDidFinishLaunching_(self, _notification) -> None:
            self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(-1.0)
            self.status_item.button().setTitle_("UI")
            if hasattr(self.status_item, "setVisible_"):
                self.status_item.setVisible_(True)
            self.controller.activate_ui()
            self.signal_timer = _install_sigint_handler(NSApp(), self.controller, NSTimer, NSObject, objc_super)

            self.controller.start()
            menu = NSMenu.alloc().init()

            self.hand_item = self._toggle_item("Hand Gesture", "toggleHand_")
            self.head_item = self._toggle_item("Head Gesture", "toggleHead_")
            self.stt_item = self._toggle_item("STT", "toggleStt_")
            self.tts_item = self._toggle_item("TTS", "toggleTts_")

            menu.addItem_(self.hand_item)
            menu.addItem_(self.head_item)
            menu.addItem_(self.stt_item)
            menu.addItem_(self.tts_item)
            menu.addItem_(NSMenuItem.separatorItem())

            self.camera_root_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Camera", None, "")
            self.camera_root_item.setSubmenu_(self._camera_submenu())
            menu.addItem_(self.camera_root_item)

            stt_model_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("STT Model", None, "")
            stt_model_item.setSubmenu_(self._model_submenu(stt_models, is_tts=False))
            menu.addItem_(stt_model_item)

            tts_model_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("TTS Model", None, "")
            tts_model_item.setSubmenu_(self._model_submenu(tts_models, is_tts=True))
            menu.addItem_(tts_model_item)
            menu.addItem_(NSMenuItem.separatorItem())

            permissions = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Permissions", "showPermissions_", "")
            permissions.setTarget_(self)
            menu.addItem_(permissions)
            open_camera_settings = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "Open Camera Settings",
                "openCameraSettings_",
                "",
            )
            open_camera_settings.setTarget_(self)
            menu.addItem_(open_camera_settings)

            open_microphone_settings = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "Open Microphone Settings",
                "openMicrophoneSettings_",
                "",
            )
            open_microphone_settings.setTarget_(self)
            menu.addItem_(open_microphone_settings)

            recalibrate = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Recalibrate", "recalibrate_", "")
            recalibrate.setTarget_(self)
            menu.addItem_(recalibrate)

            quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Quit", "quit_", "q")
            quit_item.setTarget_(self)
            menu.addItem_(quit_item)

            self._sync_toggle_states()
            self.status_item.setMenu_(menu)

        def _toggle_item(self, title: str, action_name: str):
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action_name, "")
            item.setTarget_(self)
            return item

        def _model_submenu(self, models, *, is_tts: bool):
            submenu = NSMenu.alloc().init()
            for title, model_id in models:
                item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    title,
                    "selectTtsModel_" if is_tts else "selectSttModel_",
                    "",
                )
                item.setTarget_(self)
                item.setRepresentedObject_(model_id)
                submenu.addItem_(item)
                if is_tts:
                    self.tts_model_items[model_id] = item
                else:
                    self.stt_model_items[model_id] = item
            return submenu

        def _camera_submenu(self):
            submenu = NSMenu.alloc().init()
            self.camera_items = {}
            cameras = self.controller.available_cameras()
            if not cameras:
                item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("No camera found", None, "")
                item.setEnabled_(False)
                submenu.addItem_(item)
                return submenu
            for camera in cameras:
                item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(camera.name, "selectCamera_", "")
                item.setTarget_(self)
                item.setRepresentedObject_(camera.index)
                submenu.addItem_(item)
                self.camera_items[camera.index] = item
            return submenu

        def _sync_toggle_states(self) -> None:
            toggles = self.controller.settings.config.toggles
            self.hand_item.setState_(NSControlStateValueOn if toggles.hand_enabled else NSControlStateValueOff)
            self.head_item.setState_(NSControlStateValueOn if toggles.head_enabled else NSControlStateValueOff)
            self.stt_item.setState_(NSControlStateValueOn if toggles.stt_enabled else NSControlStateValueOff)
            self.tts_item.setState_(NSControlStateValueOn if toggles.tts_enabled else NSControlStateValueOff)
            current_stt = self.controller.settings.config.speech.stt_model_id
            current_tts = self.controller.settings.config.speech.tts_model_id
            current_camera_index = self.controller.settings.config.camera_index
            for model_id, item in self.stt_model_items.items():
                item.setState_(NSControlStateValueOn if model_id == current_stt else NSControlStateValueOff)
            for model_id, item in self.tts_model_items.items():
                item.setState_(NSControlStateValueOn if model_id == current_tts else NSControlStateValueOff)
            for camera_index, item in self.camera_items.items():
                item.setState_(NSControlStateValueOn if camera_index == current_camera_index else NSControlStateValueOff)

        def toggleHand_(self, _sender) -> None:
            toggles = self.controller.settings.config.toggles
            self.controller.settings.update_toggle(hand=not toggles.hand_enabled)
            self._sync_toggle_states()

        def toggleHead_(self, _sender) -> None:
            toggles = self.controller.settings.config.toggles
            self.controller.settings.update_toggle(head=not toggles.head_enabled)
            self._sync_toggle_states()

        def toggleStt_(self, _sender) -> None:
            toggles = self.controller.settings.config.toggles
            self.controller.settings.update_toggle(stt=not toggles.stt_enabled)
            self._sync_toggle_states()

        def toggleTts_(self, _sender) -> None:
            toggles = self.controller.settings.config.toggles
            self.controller.settings.update_toggle(tts=not toggles.tts_enabled)
            self._sync_toggle_states()

        def showPermissions_(self, _sender) -> None:
            from AppKit import NSAlert

            alert = NSAlert.alloc().init()
            alert.setMessageText_("Permissions")
            alert.setInformativeText_(self.controller.request_permissions())
            alert.runModal()
            self._refresh_camera_submenu()

        def recalibrate_(self, _sender) -> None:
            self.controller.recalibrate()

        def openCameraSettings_(self, _sender) -> None:
            self.controller.open_camera_settings()

        def openMicrophoneSettings_(self, _sender) -> None:
            self.controller.open_microphone_settings()

        def selectSttModel_(self, sender) -> None:
            model_id = str(sender.representedObject())
            self.controller.settings.set_stt_model(model_id)
            self._sync_toggle_states()

        def selectTtsModel_(self, sender) -> None:
            model_id = str(sender.representedObject())
            self.controller.settings.set_tts_model(model_id)
            self._sync_toggle_states()

        def selectCamera_(self, sender) -> None:
            camera_index = int(sender.representedObject())
            self.controller.set_camera_index(camera_index)
            self._sync_toggle_states()

        def _refresh_camera_submenu(self) -> None:
            if self.camera_root_item is not None:
                self.camera_root_item.setSubmenu_(self._camera_submenu())
                self._sync_toggle_states()

        def quit_(self, _sender) -> None:
            self.controller.stop()
            NSApp().terminate_(None)

    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()


def _install_sigint_handler(app, controller, timer_class, ns_object_class, objc_super):  # pragma: no cover - runtime only
    previous_handler = signal.getsignal(signal.SIGINT)

    def handle_sigint(_signum, _frame) -> None:
        controller.stop()
        app.terminate_(None)

    signal.signal(signal.SIGINT, handle_sigint)

    class _SignalPump(ns_object_class):
        def init(self):
            self = objc_super(_SignalPump, self).init()
            return self

        def tick_(self, _timer) -> None:
            return None

    pump = _SignalPump.alloc().init()
    timer = timer_class.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        0.25,
        pump,
        "tick:",
        None,
        True,
    )
    timer._python_signal_handler = handle_sigint
    timer._previous_signal_handler = previous_handler
    timer._signal_pump = pump
    return timer
