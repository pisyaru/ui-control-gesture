from __future__ import annotations

from threading import Lock, Thread
from typing import Callable

from ui_control_gesture.app.config import AppConfig
from ui_control_gesture.app.types import CaptionAnchor, CursorPoint, SpeechMode
from ui_control_gesture.audio.interfaces import ManualRecorder, SpeechSynthBackend, TranscriptCallback, TranscriberBackend, WakeRecognizer


class SpeechCoordinator:
    def __init__(
        self,
        *,
        config: AppConfig,
        wake_recognizer: WakeRecognizer,
        recorder: ManualRecorder,
        transcriber: TranscriberBackend,
        synthesizer: SpeechSynthBackend,
        on_transcript: TranscriptCallback,
        background_runner: Callable[[Callable[[], None]], None] | None = None,
    ) -> None:
        self._config = config
        self._wake_recognizer = wake_recognizer
        self._recorder = recorder
        self._transcriber = transcriber
        self._synthesizer = synthesizer
        self._on_transcript = on_transcript
        self._head_anchor = CaptionAnchor.CENTER
        self._speech_mode = SpeechMode.IDLE
        self._cursor_anchor: CursorPoint | None = None
        self._lock = Lock()
        self._background_runner = background_runner or self._default_background_runner
        self._wake_run_id = 0

    @property
    def speech_mode(self) -> SpeechMode:
        return self._speech_mode

    def start(self) -> None:
        if self._config.toggles.stt_enabled:
            self._speech_mode = SpeechMode.WAKE_LISTENING
            self._wake_recognizer.start(self._on_wake_detected)

    def stop(self) -> None:
        self._wake_recognizer.stop()
        self._speech_mode = SpeechMode.IDLE

    def apply_config(self, config: AppConfig) -> None:
        self._config = config
        if not config.toggles.stt_enabled:
            with self._lock:
                self._wake_run_id += 1
            self._wake_recognizer.stop()
            if self._speech_mode == SpeechMode.FIST_RECORDING:
                try:
                    self._recorder.stop()
                except Exception:
                    pass
            self._speech_mode = SpeechMode.IDLE
        elif self._speech_mode == SpeechMode.IDLE:
            self.start()

    def update_head_anchor(self, anchor: CaptionAnchor) -> None:
        self._head_anchor = anchor

    def start_fist_recording(self, cursor: CursorPoint) -> bool:
        with self._lock:
            if not self._config.toggles.stt_enabled:
                return False
            if self._speech_mode not in {SpeechMode.IDLE, SpeechMode.WAKE_LISTENING}:
                return False
            self._wake_recognizer.stop()
            self._cursor_anchor = cursor
            self._recorder.start()
            self._speech_mode = SpeechMode.FIST_RECORDING
            return True

    def stop_fist_recording(self, cursor: CursorPoint) -> bool:
        with self._lock:
            if self._speech_mode != SpeechMode.FIST_RECORDING:
                return False
            self._speech_mode = SpeechMode.TRANSCRIBING
        try:
            segment = self._recorder.stop()
            text = self._transcriber.transcribe(segment, self._languages)
            target = cursor if cursor is not None else self._cursor_anchor
            if text:
                self._on_transcript(text, CaptionAnchor.CURSOR, target)
        finally:
            self._resume_wake_listening()
        return True

    def speak(self, text: str) -> None:
        if not self._config.toggles.tts_enabled:
            return
        self._speech_mode = SpeechMode.SPEAKING
        self._synthesizer.speak(text)
        self._resume_wake_listening()

    @property
    def _languages(self) -> tuple[str, ...]:
        return (self._config.speech.primary_language, *self._config.speech.secondary_languages)

    def _on_wake_detected(self, _phrase: str) -> None:
        with self._lock:
            if not self._config.toggles.stt_enabled:
                return
            if self._speech_mode not in {SpeechMode.IDLE, SpeechMode.WAKE_LISTENING}:
                return
            self._speech_mode = SpeechMode.WAKE_RECORDING
            self._wake_run_id += 1
            run_id = self._wake_run_id
            self._wake_recognizer.stop()
        self._background_runner(lambda: self._run_wake_recording(run_id))

    def _run_wake_recording(self, run_id: int) -> None:
        try:
            segment = self._recorder.record_until_silence(self._config.speech.silence_timeout_seconds)
            with self._lock:
                if run_id != self._wake_run_id or not self._config.toggles.stt_enabled:
                    return
            text = self._transcriber.transcribe(segment, self._languages)
            with self._lock:
                if run_id != self._wake_run_id or not self._config.toggles.stt_enabled:
                    return
            if text:
                self._on_transcript(text, self._head_anchor, None)
        finally:
            self._resume_wake_listening()

    def _resume_wake_listening(self) -> None:
        with self._lock:
            if self._config.toggles.stt_enabled:
                self._speech_mode = SpeechMode.WAKE_LISTENING
                self._wake_recognizer.start(self._on_wake_detected)
            else:
                self._speech_mode = SpeechMode.IDLE

    @staticmethod
    def _default_background_runner(task: Callable[[], None]) -> None:
        Thread(target=task, name="speech-coordinator-task", daemon=True).start()
