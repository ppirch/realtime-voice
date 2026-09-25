import wave

import numpy as np

from realtime_voice.record import SessionRecorder


def _recorder(tmp_path):
    return SessionRecorder(str(tmp_path), 16000, 'en', 'ielts', 2500, 120)


def test_recorder_writes_transcript_audio_and_meta(tmp_path):
    rec = _recorder(tmp_path)
    rec.mic_chunk(np.full(1600, 0.1, dtype=np.float32))
    rec.turn('user', 'hello', n=1)
    rec.turn_window(1, 100.0, 104.5)
    rec.turn('assistant', 'hi there', n=1,
             timings={'first_audio_s': 1.2, 'synth_s': 0.4, 'total_s': 1.6})
    rec.agent_audio([np.full(2400, 0.05, dtype=np.float32)], 24000)
    rec.close()

    session = next(tmp_path.iterdir())
    md = (session / 'transcript.md').read_text()
    assert '## You (turn 1)' in md and 'hello' in md
    assert '## Agent (turn 1)' in md and 'hi there' in md

    with wave.open(str(session / 'mic.wav'), 'rb') as w:
        assert (w.getnframes(), w.getframerate()) == (1600, 16000)
    with wave.open(str(session / 'agent.wav'), 'rb') as w:
        assert (w.getnframes(), w.getframerate()) == (2400, 24000)

    import json
    meta = json.loads((session / 'meta.json').read_text())
    assert meta['lang'] == 'en' and meta['preset'] == 'ielts'
    assert meta['turns'][0] == {'role': 'user', 'text': 'hello', 'turn': 1}
    assert meta['turns'][1]['mic_window'] == [100.0, 104.5]


def test_recorder_empty_session_still_finalizes(tmp_path):
    rec = _recorder(tmp_path)
    rec.close()
    session = next(tmp_path.iterdir())
    assert (session / 'transcript.md').exists()
    assert (session / 'meta.json').exists()
    assert not (session / 'mic.wav').exists()


def test_mic_texts_tap_sees_every_chunk():
    from realtime_voice.app import mic_texts
    from realtime_voice.stt_endpoint import Utterance

    seen = []

    class FakeMic:
        def chunks(self):
            yield np.zeros(1280, dtype=np.float32)
            yield np.zeros(1280, dtype=np.float32)

    class ConsumingBackend:
        def stream(self, chunks, sample_rate=16000):
            n = sum(1 for _ in chunks)
            assert n == 2
            yield Utterance('hi')

    got = list(mic_texts(ConsumingBackend(), FakeMic(), 16000, tap=seen.append))
    assert got == ['hi']
    assert len(seen) == 2
