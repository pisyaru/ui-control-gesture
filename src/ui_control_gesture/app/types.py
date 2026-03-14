from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import monotonic


class Handedness(str, Enum):
    LEFT = "left"
    RIGHT = "right"


class GestureActionType(str, Enum):
    MOVE_CURSOR = "move_cursor"
    LEFT_DOWN = "left_down"
    LEFT_UP = "left_up"
    RIGHT_DOWN = "right_down"
    RIGHT_UP = "right_up"
    SCROLL = "scroll"
    START_FIST_STT = "start_fist_stt"
    STOP_FIST_STT = "stop_fist_stt"


class CaptionAnchor(str, Enum):
    CENTER = "center"
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"
    CURSOR = "cursor"


class SpeechMode(str, Enum):
    IDLE = "idle"
    WAKE_LISTENING = "wake_listening"
    WAKE_RECORDING = "wake_recording"
    FIST_RECORDING = "fist_recording"
    TRANSCRIBING = "transcribing"
    SPEAKING = "speaking"


@dataclass(slots=True)
class CursorPoint:
    x: float
    y: float


@dataclass(slots=True)
class NormalizedPoint:
    x: float
    y: float


@dataclass(slots=True)
class ScrollDelta:
    dy: float


@dataclass(slots=True)
class GestureAction:
    kind: GestureActionType
    handedness: Handedness
    cursor: CursorPoint | None = None
    scroll: ScrollDelta | None = None


@dataclass(slots=True)
class HandObservation:
    handedness: Handedness
    palm_x: float
    palm_y: float
    palm_roll: float
    landmarks: tuple[NormalizedPoint, ...] = field(default_factory=tuple)
    index_thumb_touching: bool = False
    middle_thumb_touching: bool = False
    fist_closed: bool = False
    middle_swipe_velocity_y: float = 0.0
    confidence: float = 0.0
    timestamp: float = field(default_factory=monotonic)


@dataclass(slots=True)
class HeadObservation:
    yaw: float
    pitch: float
    confidence: float = 0.0
    timestamp: float = field(default_factory=monotonic)


@dataclass(slots=True)
class VisionSnapshot:
    hands: list[HandObservation] = field(default_factory=list)
    head: HeadObservation | None = None
    timestamp: float = field(default_factory=monotonic)


@dataclass(slots=True)
class TranscriptResult:
    text: str
    anchor: CaptionAnchor
    cursor: CursorPoint | None = None
    language: str | None = None


@dataclass(slots=True)
class HandFeedback:
    handedness: Handedness
    cursor: CursorPoint | None
    state_label: str
    skeleton_points: tuple[CursorPoint, ...] = field(default_factory=tuple)


@dataclass(slots=True)
class AppStatus:
    speech_mode: SpeechMode = SpeechMode.IDLE
    last_error: str | None = None
