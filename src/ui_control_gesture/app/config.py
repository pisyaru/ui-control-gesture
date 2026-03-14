from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_MODELS_DIR = Path("models")

DEFAULT_WAKE_PHRASES = ("hey adam", "헤이 아담")
DEFAULT_STT_MODEL = "mistralai/Voxtral-Mini-4B-Realtime-2602"
DEFAULT_TTS_MODEL = "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-8bit"
DEFAULT_WAKE_MODEL = "mlx-community/Qwen3-ASR-0.6B-4bit"


@dataclass(slots=True)
class FeatureToggles:
    hand_enabled: bool = True
    head_enabled: bool = True
    stt_enabled: bool = True
    tts_enabled: bool = False


@dataclass(slots=True)
class GestureConfig:
    cursor_gain_x: float = 1.35
    cursor_gain_y: float = 1.15
    roll_micro_adjust_gain: float = 28.0
    click_release_frames: int = 5
    drag_activation_frames: int = 1
    scroll_deadzone: float = 0.03
    caption_ttl_seconds: float = 1.5


@dataclass(slots=True)
class SpeechConfig:
    wake_phrases: tuple[str, ...] = DEFAULT_WAKE_PHRASES
    wake_model_id: str = DEFAULT_WAKE_MODEL
    stt_model_id: str = DEFAULT_STT_MODEL
    tts_model_id: str = DEFAULT_TTS_MODEL
    silence_timeout_seconds: float = 0.85
    audio_sample_rate: int = 16_000
    audio_channels: int = 1
    primary_language: str = "ko"
    secondary_languages: tuple[str, ...] = ("en", "ja")


@dataclass(slots=True)
class AppConfig:
    models_dir: Path = DEFAULT_MODELS_DIR
    hand_landmarker_asset: str = "hand_landmarker.task"
    face_landmarker_asset: str = "face_landmarker.task"
    toggles: FeatureToggles = field(default_factory=FeatureToggles)
    gesture: GestureConfig = field(default_factory=GestureConfig)
    speech: SpeechConfig = field(default_factory=SpeechConfig)


def default_config() -> AppConfig:
    return AppConfig()
