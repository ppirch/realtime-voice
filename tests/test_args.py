from realtime_voice.app import parse_args, resolve_lang_prompt
from realtime_voice.config import EN_SYSTEM_PROMPT, Settings, TH_SYSTEM_PROMPT


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
