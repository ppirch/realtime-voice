from thai_realtime_voice.audio import Microphone


def test_flush_drops_captured_audio():
    mic = Microphone()
    for i in range(5):
        mic.q.put_nowait(i)
    mic.flush()
    assert mic.q.empty()
