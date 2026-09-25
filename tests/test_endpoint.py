import numpy as np

from realtime_voice.stt_endpoint import (
    MODEL_SR,
    Endpointer,
    resample,
    utterance_stream,
)

CHUNK = 1280  # 80ms @ 16kHz


def _loud(n, amp=0.1):
    rng = np.random.default_rng(0)
    return [(rng.standard_normal(CHUNK).astype(np.float32) * amp) for _ in range(n)]


def _quiet(n):
    return [np.zeros(CHUNK, dtype=np.float32) for _ in range(n)]


def test_resample_passthrough_at_model_rate():
    x = np.ones(CHUNK, dtype=np.float32)
    out = resample(x, MODEL_SR)
    assert out.shape == (CHUNK,) and out.dtype == np.float32


def test_resample_converts_rate():
    x = np.ones(CHUNK * 2, dtype=np.float32)
    assert resample(x, 32000).shape == (CHUNK,)


def test_endpointer_needs_min_speech_then_silence():
    ep = Endpointer(silence_rms=0.02, silence_ms=400, min_speech_ms=200,
                    max_utterance_s=30)
    loud = np.full(CHUNK, 0.1, dtype=np.float32)
    quiet = np.zeros(CHUNK, dtype=np.float32)
    assert ep.feed(quiet) is False  # silence first: no turn
    assert ep.feed(loud) is False
    assert ep.feed(loud) is False  # 160ms < min_speech
    assert ep.feed(loud) is False  # 240ms speech, silence starts
    for _ in range(4):
        done = ep.feed(quiet)
    assert done is False  # 320ms < silence_ms
    assert ep.feed(quiet) is True  # 400ms: turn done


def test_endpointer_max_utterance_forces_done():
    ep = Endpointer(silence_rms=0.02, silence_ms=8000, min_speech_ms=200,
                    max_utterance_s=1)
    loud = np.full(CHUNK, 0.1, dtype=np.float32)
    done = [ep.feed(loud) for _ in range(13)]  # ~1.04s
    assert done[-1] is True
    assert all(d is False for d in done[:-1])


def test_endpointer_reset_starts_new_turn():
    ep = Endpointer(silence_rms=0.02, silence_ms=80, min_speech_ms=80,
                    max_utterance_s=30)
    loud = np.full(CHUNK, 0.1, dtype=np.float32)
    quiet = np.zeros(CHUNK, dtype=np.float32)
    assert ep.feed(loud) is False
    assert ep.feed(quiet) is True
    ep.reset()
    assert ep.feed(quiet) is False  # fresh state: silence alone never ends a turn


def test_utterance_stream_yields_finals_only():
    calls = []

    def transcribe(buf):
        calls.append(len(buf))
        return "hello"

    ep = Endpointer(silence_rms=0.02, silence_ms=400, min_speech_ms=200,
                    max_utterance_s=30)
    events = list(utterance_stream(iter(_loud(6) + _quiet(8)), 16000, ep, transcribe))
    assert [(e.text, e.is_final) for e in events] == [("hello", True)]
    assert calls == [11]  # whole turn (speech + trailing silence) in one decode


def test_utterance_stream_skips_empty_transcriptions():
    ep = Endpointer(silence_rms=0.02, silence_ms=400, min_speech_ms=200,
                    max_utterance_s=30)
    events = list(utterance_stream(iter(_loud(6) + _quiet(8)), 16000, ep,
                                   lambda buf: "  "))
    assert events == []


def test_utterance_stream_two_turns():
    ep = Endpointer(silence_rms=0.02, silence_ms=400, min_speech_ms=200,
                    max_utterance_s=30)
    chunks = _loud(6) + _quiet(8) + _loud(6) + _quiet(8)
    events = list(utterance_stream(iter(chunks), 16000, ep, lambda buf: "hi"))
    assert [(e.text, e.is_final) for e in events] == [("hi", True), ("hi", True)]
