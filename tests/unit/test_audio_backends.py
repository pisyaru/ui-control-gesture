from threading import current_thread

from ui_control_gesture.audio.backends import KeywordSpottingWakeRecognizer, MLXAudioTranscriber, _WakeFrame


def test_wake_recognizer_stop_does_not_join_current_thread_and_clears_queue() -> None:
    recognizer = KeywordSpottingWakeRecognizer(
        model_id="wake-model",
        wake_phrases=("hey adam",),
        transcriber=MLXAudioTranscriber("wake-model"),
        sample_rate=16_000,
        channels=1,
    )
    recognizer._thread = current_thread()
    recognizer._queue.append(_WakeFrame(payload=b"abc", created_at=0.0))

    recognizer.stop()

    assert list(recognizer._queue) == []
