from __future__ import annotations

from ui_control_gesture.app.types import CaptionAnchor, HeadObservation


class HeadAnchorMapper:
    def __init__(self, yaw_threshold: float = 0.08, pitch_threshold: float = 0.08) -> None:
        self._yaw_threshold = yaw_threshold
        self._pitch_threshold = pitch_threshold

    def map(self, head: HeadObservation | None) -> CaptionAnchor:
        if head is None:
            return CaptionAnchor.CENTER
        if head.yaw <= -self._yaw_threshold:
            return CaptionAnchor.LEFT
        if head.yaw >= self._yaw_threshold:
            return CaptionAnchor.RIGHT
        if head.pitch <= -self._pitch_threshold:
            return CaptionAnchor.UP
        if head.pitch >= self._pitch_threshold:
            return CaptionAnchor.DOWN
        return CaptionAnchor.CENTER


class HeadCaptionAnchorMapper(HeadAnchorMapper):
    pass
