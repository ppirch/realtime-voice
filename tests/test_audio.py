import pytest

from thai_realtime_voice.audio import Microphone
from thai_realtime_voice.stt_mlx import endpoint_threshold


def test_flush_drops_captured_audio():
    mic = Microphone()
    for i in range(5):
        mic.q.put_nowait(i)
    mic.flush()
    assert mic.q.empty()


def test_endpoint_threshold_scales_from_floor():
    assert endpoint_threshold(0.004) == pytest.approx(0.012)
    assert endpoint_threshold(0.0) == 0.008  # sane minimum
    assert endpoint_threshold(0.05) == pytest.approx(0.15)
