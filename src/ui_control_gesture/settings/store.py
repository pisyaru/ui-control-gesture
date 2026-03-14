from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

from ui_control_gesture.app.config import AppConfig, default_config


@dataclass(slots=True)
class SettingsStore:
    config: AppConfig
    _subscribers: list[Callable[[AppConfig], None]] | None = None

    @classmethod
    def create_default(cls) -> "SettingsStore":
        return cls(config=default_config())

    def set_feature_toggle(self, name: str, enabled: bool) -> None:
        if not hasattr(self.config.toggles, name):
            raise AttributeError(f"Unknown toggle: {name}")
        setattr(self.config.toggles, name, enabled)

    def set_stt_model(self, model_id: str) -> None:
        self.config.speech.stt_model_id = model_id
        self._notify()

    def set_tts_model(self, model_id: str) -> None:
        self.config.speech.tts_model_id = model_id
        self._notify()

    def update_toggle(
        self,
        *,
        hand: bool | None = None,
        head: bool | None = None,
        stt: bool | None = None,
        tts: bool | None = None,
    ) -> None:
        toggles = self.config.toggles
        if hand is not None:
            toggles.hand_enabled = hand
        if head is not None:
            toggles.head_enabled = head
        if stt is not None:
            toggles.stt_enabled = stt
        if tts is not None:
            toggles.tts_enabled = tts
        self._notify()

    def subscribe(self, callback: Callable[[AppConfig], None]) -> None:
        if self._subscribers is None:
            self._subscribers = []
        self._subscribers.append(callback)

    def _notify(self) -> None:
        if not self._subscribers:
            return
        snapshot = replace(self.config)
        for callback in self._subscribers:
            callback(snapshot)
