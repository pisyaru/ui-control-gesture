from __future__ import annotations

from ui_control_gesture.app.config import AppConfig, default_config
from ui_control_gesture.app.types import CaptionAnchor, CursorPoint, GestureActionType, VisionSnapshot
from ui_control_gesture.gesture.hand_mapper import HandGestureMapper
from ui_control_gesture.gesture.head_mapper import HeadCaptionAnchorMapper
from ui_control_gesture.overlay.renderer import AppKitOverlayWindow, OverlayRenderer
from ui_control_gesture.settings.store import SettingsStore
from ui_control_gesture.system.macos_input import QuartzMacInputController
from ui_control_gesture.system.permissions import CameraDevice, list_camera_devices, prompt_for_permissions, query_permission_state
from ui_control_gesture.vision.pipeline import MediapipeVisionPipeline


class GestureControlApplication:
    def __init__(self, config: AppConfig | None = None) -> None:
        self._config = config or default_config()
        self._settings = SettingsStore(self._config)
        self._input = QuartzMacInputController()
        self._overlay: OverlayRenderer = self._build_overlay()
        self._hand_mapper = HandGestureMapper(self._config.gesture)
        self._head_mapper = HeadCaptionAnchorMapper()
        self._current_head_anchor = CaptionAnchor.CENTER
        self._speech = self._build_speech_coordinator()
        self._vision = MediapipeVisionPipeline(self._config, self.handle_snapshot, self._handle_runtime_error)
        self._started = False
        self._vision_running = False
        self._settings.subscribe(self._handle_settings_change)

    @property
    def settings(self) -> SettingsStore:
        return self._settings

    def permission_summary(self) -> str:
        state = query_permission_state()
        return (
            f"camera={state.camera} mic={state.microphone} "
            f"accessibility={state.accessibility} input_monitoring={state.input_monitoring}"
        )

    def request_permissions(self) -> str:
        state = prompt_for_permissions()
        return (
            f"camera={state.camera} mic={state.microphone} "
            f"accessibility={state.accessibility} input_monitoring={state.input_monitoring}"
        )

    def available_cameras(self) -> list[CameraDevice]:
        return list_camera_devices()

    def start(self) -> None:
        self._started = True
        permission_state = prompt_for_permissions()
        if permission_state.microphone and self._config.toggles.stt_enabled:
            self._speech.start()
        elif self._config.toggles.stt_enabled:
            self._handle_runtime_error("microphone permission is required for STT.")

        if permission_state.camera:
            self._vision.start()
            self._vision_running = True
        else:
            self._handle_runtime_error("camera permission is required before gesture tracking can start.")

    def stop(self) -> None:
        if self._vision_running:
            self._vision.stop()
            self._vision_running = False
        self._speech.stop()
        self._started = False

    def recalibrate(self) -> None:
        self._current_head_anchor = CaptionAnchor.CENTER

    def set_camera_index(self, camera_index: int) -> None:
        self._settings.set_camera_index(camera_index)

    def handle_snapshot(self, snapshot: VisionSnapshot) -> None:
        config = self._settings.config
        if config.toggles.head_enabled:
            self._current_head_anchor = self._head_mapper.map(snapshot.head)
            self._speech.update_head_anchor(self._current_head_anchor)

        if not config.toggles.hand_enabled:
            self._overlay.show_hand_feedback([])
            return

        screen = self._input.screen_frame()
        actions, feedback = self._hand_mapper.map(snapshot.hands, screen_width=screen.width, screen_height=screen.height)
        self._overlay.show_hand_feedback(feedback)

        for action in actions:
            if action.kind == GestureActionType.MOVE_CURSOR and action.cursor is not None:
                self._input.move_cursor(action.cursor)
            elif action.kind == GestureActionType.LEFT_DOWN and action.cursor is not None:
                self._input.press_left(action.cursor)
            elif action.kind == GestureActionType.LEFT_UP and action.cursor is not None:
                self._input.release_left(action.cursor)
            elif action.kind == GestureActionType.RIGHT_DOWN and action.cursor is not None:
                self._input.press_right(action.cursor)
            elif action.kind == GestureActionType.RIGHT_UP and action.cursor is not None:
                self._input.release_right(action.cursor)
            elif action.kind == GestureActionType.SCROLL and action.scroll is not None:
                self._input.scroll(action.scroll.dy)
            elif action.kind == GestureActionType.START_FIST_STT and action.cursor is not None:
                self._speech.start_fist_recording(action.cursor)
            elif action.kind == GestureActionType.STOP_FIST_STT and action.cursor is not None:
                self._speech.stop_fist_recording(action.cursor)

    def _handle_settings_change(self, config: AppConfig) -> None:
        old_config = self._config
        self._config = config
        if (
            old_config.speech.stt_model_id != config.speech.stt_model_id
            or old_config.speech.tts_model_id != config.speech.tts_model_id
        ):
            self._speech.stop()
            self._speech = self._build_speech_coordinator()
            if config.toggles.stt_enabled:
                self._speech.start()
        else:
            self._speech.apply_config(config)

        if old_config.camera_index != config.camera_index:
            self._restart_vision()

    def _handle_transcript(self, text: str, anchor: CaptionAnchor, cursor: CursorPoint | None) -> None:
        self._overlay.show_caption(
            text=text,
            anchor=anchor,
            cursor=cursor,
            ttl_seconds=self._config.gesture.caption_ttl_seconds,
        )

    def _handle_runtime_error(self, message: str) -> None:
        self._overlay.show_caption(
            text=f"runtime error: {message}",
            anchor=CaptionAnchor.CENTER,
            cursor=None,
            ttl_seconds=max(self._config.gesture.caption_ttl_seconds, 2.5),
        )

    def _build_overlay(self) -> OverlayRenderer:
        try:
            return AppKitOverlayWindow()
        except Exception:
            return OverlayRenderer()

    def _restart_vision(self) -> None:
        if self._vision_running:
            self._vision.stop()
            self._vision_running = False
        self._vision = MediapipeVisionPipeline(self._config, self.handle_snapshot, self._handle_runtime_error)
        if self._started:
            permission_state = query_permission_state()
            if permission_state.camera:
                self._vision.start()
                self._vision_running = True
            else:
                self._handle_runtime_error("camera permission is required before gesture tracking can start.")

    def _build_speech_coordinator(self):
        from ui_control_gesture.audio.backends import build_default_audio_stack
        from ui_control_gesture.audio.coordinator import SpeechCoordinator

        wake_recognizer, recorder, transcriber, synthesizer = build_default_audio_stack(self._config)
        return SpeechCoordinator(
            config=self._config,
            wake_recognizer=wake_recognizer,
            recorder=recorder,
            transcriber=transcriber,
            synthesizer=synthesizer,
            on_transcript=self._handle_transcript,
        )


def run() -> None:
    from ui_control_gesture.app.menu import run_menu_bar_app

    run_menu_bar_app(lambda: GestureControlApplication(default_config()))
