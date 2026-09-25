import os

import realtime_voice.config as config_mod
from realtime_voice.config import Settings


def _no_dotenv(monkeypatch, tmp_path):
    # from_env()'s load_dotenv() resolves the repo .env via the caller file,
    # so neutralize it for hermetic tests
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config_mod, "load_dotenv", lambda *a, **k: False)
    for k in ("LLM_SYSTEM_PROMPT", "VOICE_LANG"):
        monkeypatch.delenv(k, raising=False)


def test_english_lang_selects_english_prompt(monkeypatch, tmp_path):
    _no_dotenv(monkeypatch, tmp_path)
    monkeypatch.setenv("VOICE_LANG", "en")
    s = Settings.from_env()
    assert s.voice_lang == "en"
    assert "English" in s.system_prompt
    assert "Thai" not in s.system_prompt


def test_default_lang_is_thai(monkeypatch, tmp_path):
    _no_dotenv(monkeypatch, tmp_path)
    s = Settings.from_env()
    assert s.voice_lang == "th"
    assert "Thai" in s.system_prompt
    assert "VOICE_LANG" not in os.environ
