from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from ui_control_gesture.app.types import CaptionAnchor, CursorPoint


@dataclass(slots=True)
class AudioSegment:
    samples: bytes
    sample_rate: int
    channels: int


TranscriptCallback = Callable[[str, CaptionAnchor, CursorPoint | None], None]
WakeCallback = Callable[[str], None]


class WakeRecognizer(Protocol):
    def start(self, on_detected: WakeCallback) -> None: ...

    def stop(self) -> None: ...


class ManualRecorder(Protocol):
    def start(self) -> None: ...

    def stop(self) -> AudioSegment: ...

    def record_until_silence(self, silence_timeout_seconds: float) -> AudioSegment: ...


class TranscriberBackend(Protocol):
    def transcribe(self, segment: AudioSegment, languages: tuple[str, ...]) -> str: ...


class SpeechSynthBackend(Protocol):
    def speak(self, text: str) -> None: ...
