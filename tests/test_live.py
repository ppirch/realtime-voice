import numpy as np

from realtime_voice.stt_live import LiveWhisperMLXBackend

SR = 16000
CHUNK = 1280  # 80ms


def _loud(n):
    rng = np.random.default_rng(0)
    return [(rng.standard_normal(CHUNK).astype(np.float32) * 0.1) for _ in range(n)]


def _quiet(n):
    return [np.zeros(CHUNK, dtype=np.float32) for _ in range(n)]


class ScriptedTranscriber:
    """Returns canned words; identical outputs on consecutive ticks."""

    def __init__(self, calls):
        self.calls = calls
        self.n = 0

    def transcribe(self, audio):
        out = self.calls[min(self.n, len(self.calls) - 1)]
        self.n += 1
        return out


# Real whisper words carry their own spacing (" world"), so the backend
# joins with "" — the stub mirrors that.
WORDS = [(0.0, 0.4, 'hello'), (0.4, 0.9, ' world')]


def _backend(calls, **kw):
    kw.setdefault('max_utterance_s', 30)
    return LiveWhisperMLXBackend(
        language='en', live_every_s=0.24, silence_rms=0.02, silence_ms=400,
        min_speech_ms=200, transcriber=ScriptedTranscriber(calls), **kw)


def test_previews_then_single_final_without_dupes():
    b = _backend([[], WORDS, WORDS, WORDS])
    chunks = _loud(12) + _quiet(8)  # ~1s speech, then silence endpoint
    events = list(b.stream(iter(chunks)))
    assert events, "expected previews + final"
    assert all(e.is_final for e in events[-1:]), "last event must be final"
    finals = [e.text for e in events if e.is_final]
    assert finals == ['hello world'], finals
    previews = [e.text for e in events if not e.is_final]
    assert previews and all(p for p in previews)
    assert all('hello' in p for p in previews)


def test_pure_silence_emits_nothing():
    b = _backend([WORDS])
    assert list(b.stream(iter(_quiet(20)))) == []


def test_short_blip_below_min_speech_ignored():
    b = _backend([WORDS])
    assert list(b.stream(iter(_loud(1) + _quiet(10)))) == []


def test_max_utterance_forces_final():
    b = _backend([WORDS, WORDS, WORDS], max_utterance_s=1)
    events = list(b.stream(iter(_loud(20))))
    finals = [e.text for e in events if e.is_final]
    assert len(finals) == 1 and finals[0] == 'hello world'
