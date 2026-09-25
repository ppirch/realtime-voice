from dataclasses import dataclass
import os

from dotenv import load_dotenv


TH_SYSTEM_PROMPT = (
    "You are a realtime Thai voice assistant. Reply in spoken Thai only: "
    "1-2 short sentences per turn, under 60 characters when possible. "
    "Never use lists, markdown, emoji, URLs, or symbols. "
    "Write numbers as Thai words. "
    "One idea per turn, then ask a brief follow-up to keep talking."
)
EN_SYSTEM_PROMPT = (
    "You are a realtime English voice assistant. Reply in spoken English only: "
    "1-2 short sentences per turn, under 60 characters when possible. "
    "Never use lists, markdown, emoji, URLs, or symbols. One idea per turn, "
    "then ask a brief follow-up to keep talking."
)
IELTS_EXAMINER_PROMPT = (
    "You are an IELTS speaking examiner running a mock test in spoken English only. "
    "Part 1: ask 4-5 short questions on familiar topics, one per turn. "
    "Part 2: give a cue-card topic, let the candidate speak, then ask 1-2 follow-ups. "
    "Part 3: ask 4-5 deeper discussion questions, one per turn. "
    "Ask exactly one question per turn and wait. Keep every message under 40 words: "
    "plain speakable sentences only, no lists, markdown, emoji, or symbols. "
    "Do not correct or score until asked; when asked, give band scores for fluency, "
    "vocabulary, grammar, and pronunciation with one tip each."
)
PRESETS = {"ielts": IELTS_EXAMINER_PROMPT}
PRESET_LANG = {"ielts": "en"}


@dataclass(frozen=True)
class Settings:
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    llm_protocol: str
    system_prompt: str
    max_tokens: int = 1000
    reasoning_effort: str = ""
    voice_lang: str = "th"
    sample_rate: int = 16000
    input_chunk_ms: int = 80
    tts_sample_rate: int = 24000

    @classmethod
    def from_env(cls):
        load_dotenv()
        voice_lang = os.getenv("VOICE_LANG", "th")
        default_prompt = EN_SYSTEM_PROMPT if voice_lang == "en" else TH_SYSTEM_PROMPT
        return cls(
            os.getenv("LLM_BASE_URL", "http://localhost:8000/v1").rstrip("/"),
            os.getenv("LLM_API_KEY") or os.getenv("OPENCODE_API_KEY", ""),
            os.getenv("LLM_MODEL", ""),
            os.getenv("LLM_PROTOCOL", "responses"),
            os.getenv("LLM_SYSTEM_PROMPT", default_prompt),
            int(os.getenv("LLM_MAX_TOKENS", "1000")),
            os.getenv("LLM_REASONING_EFFORT", ""),
            voice_lang,
            int(os.getenv("SAMPLE_RATE", "16000")),
            int(os.getenv("INPUT_CHUNK_MS", "80")),
            int(os.getenv("TTS_SAMPLE_RATE", "24000")),
        )
