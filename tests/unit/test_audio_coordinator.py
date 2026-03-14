from ui_control_gesture.app.config import default_config
from ui_control_gesture.app.types import CaptionAnchor, CursorPoint, SpeechMode
from ui_control_gesture.audio.coordinator import SpeechCoordinator
from ui_control_gesture.audio.interfaces import AudioSegment


class FakeWakeRecognizer:
    def __init__(self) -> None:
        self.started = 0
        self.stopped = 0
        self.callback = None

    def start(self, on_detected) -> None:
        self.started += 1
        self.callback = on_detected

    def stop(self) -> None:
        self.stopped += 1


class FakeRecorder:
    def __init__(self) -> None:
        self.started = 0
        self.stopped = 0
        self.until_silence = 0

    def start(self) -> None:
        self.started += 1

    def stop(self) -> AudioSegment:
        self.stopped += 1
        return AudioSegment(samples=b"fist", sample_rate=16_000, channels=1)

    def record_until_silence(self, silence_timeout_seconds: float) -> AudioSegment:
        self.until_silence += 1
        return AudioSegment(samples=b"wake", sample_rate=16_000, channels=1)


class FakeTranscriber:
    def __init__(self) -> None:
        self.calls = []

    def transcribe(self, segment: AudioSegment, languages: tuple[str, ...]) -> str:
        self.calls.append((segment.samples, languages))
        return "transcribed text"


class FakeSynth:
    def __init__(self) -> None:
        self.spoken = []

    def speak(self, text: str) -> None:
        self.spoken.append(text)


def test_fist_recording_blocks_wake_and_emits_cursor_caption() -> None:
    wake = FakeWakeRecognizer()
    recorder = FakeRecorder()
    transcriber = FakeTranscriber()
    synth = FakeSynth()
    emitted = []
    coordinator = SpeechCoordinator(
        config=default_config(),
        wake_recognizer=wake,
        recorder=recorder,
        transcriber=transcriber,
        synthesizer=synth,
        on_transcript=lambda text, anchor, cursor: emitted.append((text, anchor, cursor)),
        background_runner=lambda task: task(),
    )

    coordinator.start()
    cursor = CursorPoint(x=10, y=20)

    assert coordinator.start_fist_recording(cursor) is True
    assert coordinator.speech_mode == SpeechMode.FIST_RECORDING
    assert wake.stopped >= 1

    assert coordinator.stop_fist_recording(cursor) is True
    assert emitted == [("transcribed text", CaptionAnchor.CURSOR, cursor)]
    assert coordinator.speech_mode == SpeechMode.WAKE_LISTENING


def test_wake_detected_records_until_silence_and_uses_head_anchor() -> None:
    wake = FakeWakeRecognizer()
    recorder = FakeRecorder()
    transcriber = FakeTranscriber()
    synth = FakeSynth()
    emitted = []
    coordinator = SpeechCoordinator(
        config=default_config(),
        wake_recognizer=wake,
        recorder=recorder,
        transcriber=transcriber,
        synthesizer=synth,
        on_transcript=lambda text, anchor, cursor: emitted.append((text, anchor, cursor)),
        background_runner=lambda task: task(),
    )

    coordinator.start()
    coordinator.update_head_anchor(CaptionAnchor.LEFT)

    wake.callback("hey adam")

    assert recorder.until_silence == 1
    assert emitted == [("transcribed text", CaptionAnchor.LEFT, None)]
    assert coordinator.speech_mode == SpeechMode.WAKE_LISTENING


def test_fist_cannot_start_while_wake_recording_active() -> None:
    wake = FakeWakeRecognizer()
    recorder = FakeRecorder()
    transcriber = FakeTranscriber()
    synth = FakeSynth()
    coordinator = SpeechCoordinator(
        config=default_config(),
        wake_recognizer=wake,
        recorder=recorder,
        transcriber=transcriber,
        synthesizer=synth,
        on_transcript=lambda *_args: None,
        background_runner=lambda _task: None,
    )

    coordinator.start()
    wake.callback("hey adam")

    assert coordinator.speech_mode == SpeechMode.WAKE_RECORDING
    assert coordinator.start_fist_recording(CursorPoint(x=0, y=0)) is False


def test_disabling_stt_discards_inflight_wake_result() -> None:
    wake = FakeWakeRecognizer()
    recorder = FakeRecorder()
    transcriber = FakeTranscriber()
    synth = FakeSynth()
    emitted = []
    coordinator = SpeechCoordinator(
        config=default_config(),
        wake_recognizer=wake,
        recorder=recorder,
        transcriber=transcriber,
        synthesizer=synth,
        on_transcript=lambda text, anchor, cursor: emitted.append((text, anchor, cursor)),
        background_runner=lambda _task: None,
    )

    coordinator.start()
    wake.callback("hey adam")
    disabled = default_config()
    disabled.toggles.stt_enabled = False
    coordinator.apply_config(disabled)
    coordinator._run_wake_recording(coordinator._wake_run_id - 1)

    assert emitted == []
    assert coordinator.speech_mode == SpeechMode.IDLE
