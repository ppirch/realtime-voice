from realtime_voice.app import (
    build_backend,
    listening_msg,
    parse_args,
    resolve_endpoint,
    resolve_lang_prompt,
)
from realtime_voice.config import EN_SYSTEM_PROMPT, TH_SYSTEM_PROMPT, Settings
from realtime_voice.stt_mlx import Utterance


def _settings(prompt="ENV PROMPT", lang="th"):
    return Settings("http://x", "k", "m", "p", prompt, 100, "", lang, 16000, 80, 24000)


def test_no_flags_keeps_env():
    s = _settings()
    assert resolve_lang_prompt(parse_args([]), s) == ("th", "ENV PROMPT")


def test_lang_flag_selects_builtin_prompt_over_env():
    s = _settings(prompt="ENV PROMPT", lang="th")
    assert resolve_lang_prompt(parse_args(["--lang", "en"]), s) == ("en", EN_SYSTEM_PROMPT)
    assert resolve_lang_prompt(parse_args(["--lang", "th"]), s) == ("th", TH_SYSTEM_PROMPT)


def test_system_prompt_flag_wins_over_everything():
    s = _settings(prompt="ENV PROMPT", lang="th")
    assert resolve_lang_prompt(parse_args(["--lang", "en", "--system-prompt", "CUSTOM"]), s) == ("en", "CUSTOM")
    assert resolve_lang_prompt(parse_args(["--system-prompt", "CUSTOM"]), s) == ("th", "CUSTOM")


def test_ielts_preset_implies_english():
    from realtime_voice.config import IELTS_EXAMINER_PROMPT
    s = _settings(prompt="ENV PROMPT", lang="th")
    lang, prompt = resolve_lang_prompt(parse_args(["--preset", "ielts"]), s)
    assert lang == "en" and prompt == IELTS_EXAMINER_PROMPT
    assert "Part 1" in prompt
    # explicit lang still wins for backends
    lang, _ = resolve_lang_prompt(parse_args(["--preset", "ielts", "--lang", "th"]), s)
    assert lang == "th"


def test_endpoint_defaults_without_preset():
    s = _settings()
    assert resolve_endpoint(parse_args([]), s) == (800, 15)


def test_ielts_preset_uses_patient_endpointing():
    s = _settings()
    assert resolve_endpoint(parse_args(["--preset", "ielts"]), s) == (2500, 120)


def test_explicit_endpoint_flags_win_over_preset():
    s = _settings()
    args = parse_args(["--preset", "ielts", "--silence-ms", "1200",
                       "--max-utterance-s", "60"])
    assert resolve_endpoint(args, s) == (1200, 60)


def test_listening_msg_shows_pause():
    assert listening_msg(800) == "[listening — speak, then pause ~0.8s to send]"
    assert listening_msg(2500) == "[listening — speak, then pause ~2.5s to send]"


def test_live_flag_selects_streaming_backend():
    from unittest.mock import patch

    from realtime_voice.stt_live import LiveWhisperMLXBackend
    from realtime_voice.stt_mlx import Qwen3ASRMLXBackend
    s = _settings()
    args = parse_args(["--live"])
    assert args.live is True
    assert parse_args([]).live is False
    with patch("realtime_voice.stt_live.MLXTranscriber"):
        live = build_backend(args, s, Qwen3ASRMLXBackend, 0.02, 800, 15)
        assert isinstance(live, LiveWhisperMLXBackend)
        assert live.language == "th"

    class FakeBackend:
        def __init__(self, **kw):
            self.kw = kw

    plain = build_backend(parse_args([]), s, FakeBackend, 0.02, 800, 15)
    assert isinstance(plain, FakeBackend)
    assert (plain.kw["silence_ms"], plain.kw["max_utterance_s"]) == (800, 15)


def test_mic_texts_routes_previews_to_callback():
    from realtime_voice.app import mic_texts

    class FakeASR:
        def stream(self, chunks, sample_rate=16000):
            yield Utterance("hel", is_final=False)
            yield Utterance("hello", is_final=False)
            yield Utterance("hello", is_final=True)

    class FakeMic:
        def chunks(self):
            return iter([])

    seen = []
    got = list(mic_texts(FakeASR(), FakeMic(), 16000, on_preview=seen.append))
    assert got == ["hello"]
    assert seen == ["hel", "hello"]


def test_mic_texts_ignores_previews_without_callback():
    from realtime_voice.app import mic_texts

    class FakeASR:
        def stream(self, chunks, sample_rate=16000):
            yield Utterance("hel", is_final=False)
            yield Utterance("hello", is_final=True)

    class FakeMic:
        def chunks(self):
            return iter([])

    assert list(mic_texts(FakeASR(), FakeMic(), 16000)) == ["hello"]


def test_build_voice_dispatches_per_language():
    from unittest.mock import patch

    from realtime_voice.app import build_voice
    from realtime_voice.stt_mlx import Qwen3ASRMLXBackend
    from realtime_voice.stt_parakeet import ParakeetMLXBackend
    with patch("realtime_voice.app.KokoroTTS") as kokoro, \
         patch("realtime_voice.app.MMSThaiTTS") as mms:
        cls, tts = build_voice(_settings(lang="en"))
        assert cls is ParakeetMLXBackend and tts is kokoro.return_value
        cls, tts = build_voice(_settings(lang="th"))
        assert cls is Qwen3ASRMLXBackend and tts is mms.return_value
