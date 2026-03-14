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
        toggles = replace(self.config.toggles, **{name: enabled})
        self.config = replace(self.config, toggles=toggles)
        self._notify()

    def set_stt_model(self, model_id: str) -> None:
        speech = replace(self.config.speech, stt_model_id=model_id)
        self.config = replace(self.config, speech=speech)
        self._notify()

    def set_tts_model(self, model_id: str) -> None:
        speech = replace(self.config.speech, tts_model_id=model_id)
        self.config = replace(self.config, speech=speech)
        self._notify()

    def set_camera_index(self, camera_index: int) -> None:
        self.config = replace(self.config, camera_index=camera_index)
        self._notify()

    def update_toggle(
        self,
        *,
        hand: bool | None = None,
        head: bool | None = None,
        stt: bool | None = None,
        tts: bool | None = None,
    ) -> None:
        toggles = replace(
            self.config.toggles,
            hand_enabled=self.config.toggles.hand_enabled if hand is None else hand,
            head_enabled=self.config.toggles.head_enabled if head is None else head,
            stt_enabled=self.config.toggles.stt_enabled if stt is None else stt,
            tts_enabled=self.config.toggles.tts_enabled if tts is None else tts,
        )
        self.config = replace(self.config, toggles=toggles)
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
