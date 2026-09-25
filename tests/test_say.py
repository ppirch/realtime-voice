import wave

import numpy as np
import pytest

from realtime_voice.say import parse_args, speak


class FakeTTS:
    def __init__(self):
        self.chunks = []

    def synthesize(self, text):
        self.chunks.append(text)
        return np.ones(240, dtype=np.float32)


class FakeSpeaker:
    def __init__(self):
        self.played = []

    def play(self, audio):
        self.played.append(np.asarray(audio))


def test_speak_plays_each_sentence_chunk():
    audio = speak("Hello. How are you?", tts=FakeTTS(),
                  speaker=FakeSpeaker())
    assert len(audio) == 480


def test_speak_chunks_match_and_stream_in_order():
    tts, spk = FakeTTS(), FakeSpeaker()
    speak("Hello. How are you?", tts=tts, speaker=spk)
    assert tts.chunks == ["Hello.", " How are you?"]
    assert len(spk.played) == 2


def test_speak_mute_skips_playback_but_saves_wav(tmp_path):
    out = str(tmp_path / "say.wav")
    speak("Hello.", mute=True, out=out, tts=FakeTTS(),
          speaker=FakeSpeaker())
    with wave.open(out, 'rb') as f:
        assert f.getnchannels() == 1
        assert f.getframerate() == 24000
        assert f.getnframes() == 240


def test_speak_mute_without_out_exits():
    with pytest.raises(SystemExit):
        speak("Hello.", mute=True, tts=FakeTTS(),
              speaker=FakeSpeaker())


def test_say_defaults_to_thai():
    assert parse_args(["hi"]).lang == "th"
