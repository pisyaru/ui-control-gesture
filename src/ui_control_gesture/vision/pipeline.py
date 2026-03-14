from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Thread
from time import monotonic, sleep
from typing import Callable

from ui_control_gesture.app.types import HandObservation, Handedness, HeadObservation, VisionSnapshot


def _load_cv2():
    try:
        import cv2
    except ImportError:  # pragma: no cover - dependency optional during tests
        return None
    return cv2


def _load_mediapipe():
    try:
        import mediapipe as mp
    except ImportError:  # pragma: no cover - dependency optional during tests
        return None
    return mp


@dataclass(slots=True)
class MediaPipeModels:
    hand_model_path: Path
    face_model_path: Path


class MediaPipeVisionPipeline:
    def __init__(self, models: MediaPipeModels) -> None:
        self._models = models
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._previous_middle_tip_y: dict[Handedness, float] = {}
        self._on_error: Callable[[str], None] | None = None

    def start(self, on_snapshot: Callable[[VisionSnapshot], None], on_error: Callable[[str], None] | None = None) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._on_error = on_error
        self._thread = Thread(target=self._run_guarded, args=(on_snapshot,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _run_guarded(self, on_snapshot: Callable[[VisionSnapshot], None]) -> None:  # pragma: no cover - hardware runtime
        try:
            self._run(on_snapshot)
        except Exception as exc:
            if self._on_error is not None:
                self._on_error(str(exc))

    def _run(self, on_snapshot: Callable[[VisionSnapshot], None]) -> None:  # pragma: no cover - hardware runtime
        cv2 = _load_cv2()
        mp = _load_mediapipe()
        if cv2 is None or mp is None:
            raise RuntimeError("OpenCV and mediapipe are required to run the vision pipeline.")

        base_options = mp.tasks.BaseOptions
        running_mode = mp.tasks.vision.RunningMode
        hand_options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=base_options(model_asset_path=str(self._models.hand_model_path)),
            running_mode=running_mode.VIDEO,
            num_hands=2,
        )
        face_options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=base_options(model_asset_path=str(self._models.face_model_path)),
            running_mode=running_mode.VIDEO,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
        )

        with (
            mp.tasks.vision.HandLandmarker.create_from_options(hand_options) as hand_landmarker,
            mp.tasks.vision.FaceLandmarker.create_from_options(face_options) as face_landmarker,
        ):
            camera = cv2.VideoCapture(0)
            if not camera.isOpened():
                raise RuntimeError("Unable to open the default camera.")

            while not self._stop_event.is_set():
                ok, frame = camera.read()
                if not ok:
                    sleep(0.03)
                    continue
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                timestamp_ms = int(monotonic() * 1000)
                hand_result = hand_landmarker.detect_for_video(mp_image, timestamp_ms)
                face_result = face_landmarker.detect_for_video(mp_image, timestamp_ms)
                on_snapshot(self._snapshot_from_results(hand_result, face_result))

            camera.release()

    def _snapshot_from_results(self, hand_result, face_result) -> VisionSnapshot:
        hands: list[HandObservation] = []
        for idx, landmarks in enumerate(hand_result.hand_landmarks):
            handedness_label = hand_result.handedness[idx][0].category_name.lower()
            handedness = Handedness.LEFT if handedness_label == "left" else Handedness.RIGHT
            wrist = landmarks[0]
            index_tip = landmarks[8]
            middle_tip = landmarks[12]
            thumb_tip = landmarks[4]
            index_mcp = landmarks[5]
            pinky_mcp = landmarks[17]
            palm_roll = math.atan2(pinky_mcp.y - index_mcp.y, pinky_mcp.x - index_mcp.x)
            middle_velocity = 0.0
            previous_y = self._previous_middle_tip_y.get(handedness)
            if previous_y is not None:
                middle_velocity = previous_y - middle_tip.y
            self._previous_middle_tip_y[handedness] = middle_tip.y
            fingertip_distances = [
                abs(landmarks[tip].x - wrist.x) + abs(landmarks[tip].y - wrist.y)
                for tip in (8, 12, 16, 20)
            ]
            hands.append(
                HandObservation(
                    handedness=handedness,
                    palm_x=wrist.x,
                    palm_y=wrist.y,
                    palm_roll=palm_roll,
                    index_thumb_touching=_distance(index_tip, thumb_tip) < 0.05,
                    middle_thumb_touching=_distance(middle_tip, thumb_tip) < 0.05,
                    fist_closed=max(fingertip_distances) < 0.25,
                    middle_swipe_velocity_y=middle_velocity,
                    confidence=float(hand_result.handedness[idx][0].score),
                )
            )

        head = None
        if face_result.face_landmarks:
            landmarks = face_result.face_landmarks[0]
            nose = landmarks[1]
            left_eye = landmarks[33]
            right_eye = landmarks[263]
            mouth = landmarks[13]
            eye_center_x = (left_eye.x + right_eye.x) / 2.0
            eye_center_y = (left_eye.y + right_eye.y) / 2.0
            head = HeadObservation(
                yaw=(nose.x - eye_center_x) * 1.8,
                pitch=(nose.y - (eye_center_y + mouth.y) / 2.0) * 1.6,
                confidence=1.0,
            )
        return VisionSnapshot(hands=hands, head=head)


def _distance(a, b) -> float:
    return float(math.hypot(a.x - b.x, a.y - b.y))


class MediapipeVisionPipeline:
    def __init__(self, config, on_snapshot: Callable[[VisionSnapshot], None], on_error: Callable[[str], None] | None = None) -> None:
        models_dir = Path(config.models_dir)
        self._delegate = MediaPipeVisionPipeline(
            MediaPipeModels(
                hand_model_path=models_dir / "hand_landmarker.task",
                face_model_path=models_dir / "face_landmarker.task",
            )
        )
        self._on_snapshot = on_snapshot
        self._on_error = on_error

    def start(self) -> None:
        self._delegate.start(self._on_snapshot, self._on_error)

    def stop(self) -> None:
        self._delegate.stop()
