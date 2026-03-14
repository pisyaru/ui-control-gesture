from __future__ import annotations

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
        from Foundation import NSObject
        from objc import super as objc_super
    except Exception as exc:  # pragma: no cover - macOS-only path
        raise RuntimeError("PyObjC AppKit is required to run the menu bar app.") from exc

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
            return self

        def applicationDidFinishLaunching_(self, _notification) -> None:
            self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(-1.0)
            self.status_item.button().setTitle_("UI")

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

            recalibrate = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Recalibrate", "recalibrate_", "")
            recalibrate.setTarget_(self)
            menu.addItem_(recalibrate)

            quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Quit", "quit_", "q")
            quit_item.setTarget_(self)
            menu.addItem_(quit_item)

            self.status_item.setMenu_(menu)
            self._sync_toggle_states()
            self.controller.start()

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

        def _sync_toggle_states(self) -> None:
            toggles = self.controller.settings.config.toggles
            self.hand_item.setState_(NSControlStateValueOn if toggles.hand_enabled else NSControlStateValueOff)
            self.head_item.setState_(NSControlStateValueOn if toggles.head_enabled else NSControlStateValueOff)
            self.stt_item.setState_(NSControlStateValueOn if toggles.stt_enabled else NSControlStateValueOff)
            self.tts_item.setState_(NSControlStateValueOn if toggles.tts_enabled else NSControlStateValueOff)
            current_stt = self.controller.settings.config.speech.stt_model_id
            current_tts = self.controller.settings.config.speech.tts_model_id
            for model_id, item in self.stt_model_items.items():
                item.setState_(NSControlStateValueOn if model_id == current_stt else NSControlStateValueOff)
            for model_id, item in self.tts_model_items.items():
                item.setState_(NSControlStateValueOn if model_id == current_tts else NSControlStateValueOff)

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

        def recalibrate_(self, _sender) -> None:
            self.controller.recalibrate()

        def selectSttModel_(self, sender) -> None:
            model_id = str(sender.representedObject())
            self.controller.settings.set_stt_model(model_id)
            self._sync_toggle_states()

        def selectTtsModel_(self, sender) -> None:
            model_id = str(sender.representedObject())
            self.controller.settings.set_tts_model(model_id)
            self._sync_toggle_states()

        def quit_(self, _sender) -> None:
            self.controller.stop()
            NSApp().terminate_(None)

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()
