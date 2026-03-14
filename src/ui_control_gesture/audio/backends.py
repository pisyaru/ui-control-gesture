from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Event, Lock, Thread, current_thread
from time import monotonic, sleep
import wave

from ui_control_gesture.app.config import AppConfig
from ui_control_gesture.audio.interfaces import AudioSegment


class AudioBackendUnavailable(RuntimeError):
    """Raised when local audio backends are unavailable."""


def build_default_audio_stack(config: AppConfig):
    wake_transcriber = MLXAudioTranscriber(config.speech.wake_model_id)
    wake_recognizer = KeywordSpottingWakeRecognizer(
        model_id=config.speech.wake_model_id,
        wake_phrases=config.speech.wake_phrases,
        transcriber=wake_transcriber,
        sample_rate=config.speech.audio_sample_rate,
        channels=config.speech.audio_channels,
    )
    recorder = SoundDeviceRecorder(
        sample_rate=config.speech.audio_sample_rate,
        channels=config.speech.audio_channels,
    )
    transcriber = MLXAudioTranscriber(config.speech.stt_model_id)
    synthesizer = MLXAudioSpeechSynthesizer(config.speech.tts_model_id)
    return wake_recognizer, recorder, transcriber, synthesizer


class MLXAudioTranscriber:
    def __init__(self, model_id: str) -> None:
        self._model_id = model_id
        self._loaded_model = None
        self._lock = Lock()

    def transcribe(self, segment: AudioSegment, languages: tuple[str, ...]) -> str:
        mlx_audio = self._require_mlx_audio()
        with self._lock:
            model = self._load_model(mlx_audio)
            transcript = self._transcribe_with_fallbacks(mlx_audio, model, segment, languages)
            if isinstance(transcript, dict):
                return str(transcript.get("text", "")).strip()
            return str(transcript).strip()

    def _load_model(self, mlx_audio):
        if self._loaded_model is not None:
            return self._loaded_model
        loader = getattr(mlx_audio, "load_model", None) or getattr(mlx_audio, "load", None)
        if loader is None:
            raise AudioBackendUnavailable("mlx-audio does not expose a supported model loader.")
        self._loaded_model = loader(self._model_id)
        return self._loaded_model

    @staticmethod
    def _call_first_available(mlx_audio, *, candidates: tuple[str, ...], model, kwargs):
        for name in candidates:
            fn = getattr(mlx_audio, name, None)
            if fn is None:
                continue
            try:
                return fn(model=model, **kwargs)
            except TypeError:
                try:
                    return fn(model, **kwargs)
                except TypeError:
                    continue
        raise AudioBackendUnavailable("mlx-audio does not expose a supported transcription API.")

    def _transcribe_with_fallbacks(self, mlx_audio, model, segment: AudioSegment, languages: tuple[str, ...]):
        common_kwargs = {
            "sample_rate": segment.sample_rate,
            "language": languages[0] if languages else None,
        }
        with NamedTemporaryFile(suffix=".wav", delete=True) as handle:
            self._write_wav(Path(handle.name), segment)
            for kwargs in (
                {"audio_path": handle.name, **common_kwargs},
                {"path": handle.name, **common_kwargs},
                {"audio": handle.name, **common_kwargs},
                {"audio": segment.samples, **common_kwargs},
            ):
                try:
                    return self._call_first_available(
                        mlx_audio,
                        candidates=("transcribe", "generate"),
                        model=model,
                        kwargs=kwargs,
                    )
                except AudioBackendUnavailable:
                    continue
        raise AudioBackendUnavailable("Unable to find a working mlx-audio transcription call pattern.")

    @staticmethod
    def _write_wav(path: Path, segment: AudioSegment) -> None:
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(segment.channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(segment.sample_rate)
            wav_file.writeframes(segment.samples)

    @staticmethod
    def _require_mlx_audio():
        try:
            import mlx_audio
        except Exception as exc:  # pragma: no cover - optional dependency
            raise AudioBackendUnavailable("mlx-audio is required for STT/TTS backends.") from exc
        return mlx_audio


class MLXAudioSpeechSynthesizer:
    def __init__(self, model_id: str) -> None:
        self._model_id = model_id
        self._loaded_model = None
        self._lock = Lock()

    def speak(self, text: str) -> None:
        mlx_audio = MLXAudioTranscriber._require_mlx_audio()
        with self._lock:
            model = self._load_model(mlx_audio)
            for name in ("synthesize", "speak", "generate_audio"):
                fn = getattr(mlx_audio, name, None)
                if fn is None:
                    continue
                try:
                    fn(model=model, text=text)
                    return
                except TypeError:
                    try:
                        fn(model, text)
                        return
                    except TypeError:
                        continue
        raise AudioBackendUnavailable("mlx-audio does not expose a supported speech synthesis API.")

    def _load_model(self, mlx_audio):
        if self._loaded_model is not None:
            return self._loaded_model
        loader = getattr(mlx_audio, "load_model", None) or getattr(mlx_audio, "load", None)
        if loader is None:
            raise AudioBackendUnavailable("mlx-audio does not expose a supported model loader.")
        self._loaded_model = loader(self._model_id)
        return self._loaded_model


class SoundDeviceRecorder:
    def __init__(self, sample_rate: int, channels: int) -> None:
        self._sample_rate = sample_rate
        self._channels = channels
        self._stop = Event()
        self._stream = None
        self._frames: list[bytes] = []
        self._thread: Thread | None = None

    def start(self) -> None:
        self._stop.clear()
        self._frames = []
        self._thread = Thread(target=self._record_loop, name="manual-recorder", daemon=True)
        self._thread.start()

    def stop(self) -> AudioSegment:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        return AudioSegment(samples=b"".join(self._frames), sample_rate=self._sample_rate, channels=self._channels)

    def record_until_silence(self, silence_timeout_seconds: float) -> AudioSegment:
        sounddevice = self._require_sounddevice()
        silence_started: float | None = None
        frames: list[bytes] = []

        def callback(indata, _frames_count, _time, _status):  # pragma: no cover - requires microphone
            nonlocal silence_started
            chunk = bytes(indata)
            frames.append(chunk)
            rms = self._rms(indata)
            if rms > 0.01:
                silence_started = None
            elif silence_started is None:
                silence_started = monotonic()

        with sounddevice.RawInputStream(
            samplerate=self._sample_rate,
            channels=self._channels,
            dtype="int16",
            callback=callback,
        ):  # pragma: no cover - requires microphone
            while True:
                sleep(0.05)
                if silence_started is not None and monotonic() - silence_started >= silence_timeout_seconds:
                    break
        return AudioSegment(samples=b"".join(frames), sample_rate=self._sample_rate, channels=self._channels)

    def _record_loop(self) -> None:
        sounddevice = self._require_sounddevice()

        def callback(indata, _frames_count, _time, _status):  # pragma: no cover - requires microphone
            self._frames.append(bytes(indata))

        with sounddevice.RawInputStream(
            samplerate=self._sample_rate,
            channels=self._channels,
            dtype="int16",
            callback=callback,
        ):  # pragma: no cover - requires microphone
            while not self._stop.is_set():
                sleep(0.02)

    @staticmethod
    def _rms(indata) -> float:
        try:
            import numpy as np
        except Exception as exc:  # pragma: no cover - dependency issue
            raise AudioBackendUnavailable("numpy is required for silence detection.") from exc
        values = np.frombuffer(bytes(indata), dtype=np.int16).astype("float32")
        if values.size == 0:
            return 0.0
        return float(np.sqrt((values * values).mean()) / 32768.0)

    @staticmethod
    def _require_sounddevice():
        try:
            import sounddevice
        except Exception as exc:  # pragma: no cover - optional dependency
            raise AudioBackendUnavailable("sounddevice is required for microphone capture.") from exc
        return sounddevice


@dataclass(slots=True)
class _WakeFrame:
    payload: bytes
    created_at: float


class KeywordSpottingWakeRecognizer:
    def __init__(
        self,
        *,
        model_id: str,
        wake_phrases: tuple[str, ...],
        transcriber: MLXAudioTranscriber,
        sample_rate: int,
        channels: int,
    ) -> None:
        self._model_id = model_id
        self._wake_phrases = tuple(self._normalize_phrase(item) for item in wake_phrases)
        self._transcriber = transcriber
        self._sample_rate = sample_rate
        self._channels = channels
        self._stop = Event()
        self._thread: Thread | None = None
        self._callback = None
        self._queue: deque[_WakeFrame] = deque(maxlen=6)

    def start(self, on_detected) -> None:
        self._callback = on_detected
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._queue.clear()
        self._thread = Thread(target=self._listen_loop, name="wake-recognizer", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._queue.clear()
        if self._thread is not None and self._thread is not current_thread():
            self._thread.join(timeout=3.0)
        if self._thread is not None and not self._thread.is_alive():
            self._thread = None

    def _listen_loop(self) -> None:
        sounddevice = SoundDeviceRecorder._require_sounddevice()

        def callback(indata, _frames_count, _time, _status):  # pragma: no cover - requires microphone
            if SoundDeviceRecorder._rms(indata) <= 0.01:
                return
            self._queue.append(_WakeFrame(payload=bytes(indata), created_at=monotonic()))

        with sounddevice.RawInputStream(
            samplerate=self._sample_rate,
            channels=self._channels,
            dtype="int16",
            callback=callback,
            blocksize=int(self._sample_rate * 0.5),
        ):  # pragma: no cover - requires microphone
            try:
                while not self._stop.is_set():
                    sleep(0.2)
                    if len(self._queue) < 2:
                        continue
                    segment = AudioSegment(
                        samples=b"".join(frame.payload for frame in list(self._queue)),
                        sample_rate=self._sample_rate,
                        channels=self._channels,
                    )
                    try:
                        text = self._transcriber.transcribe(segment, ("ko", "en", "ja"))
                    except Exception:
                        self._queue.clear()
                        continue
                    matched = self._match_phrase(text)
                    if matched and self._callback is not None:
                        self._queue.clear()
                        self._callback(matched)
            finally:
                self._queue.clear()

    def _match_phrase(self, text: str) -> str | None:
        normalized = self._normalize_phrase(text)
        for wake_phrase in self._wake_phrases:
            if wake_phrase in normalized:
                return wake_phrase
        return None

    @staticmethod
    def _normalize_phrase(text: str) -> str:
        return "".join(character for character in text.lower() if character.isalnum() or "\uac00" <= character <= "\ud7a3")
