import os
from dataclasses import dataclass

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
    "vocabulary, grammar, and pronunciation with one tip each. "
    "Track which part you are in and never go back to an earlier part. "
    "Director notes may arrive as system messages; obey them immediately."
)
IELTS_PART1_END = 4  # user turns: Part 1 Q&A, then cue card
IELTS_PART2_END = 7  # + long answer and 2 follow-ups, then Part 3
IELTS_WRAP_AT = 12  # wind down and offer band scores


IELTS_SCORING_PROMPT = (
    "You are an IELTS speaking examiner giving final band scores. "
    "Base your assessment ONLY on the candidate's turns in the full transcript below, "
    "which covers the whole test uncompressed. Quote 1-2 of the candidate's actual "
    "mistakes or strong phrases per criterion as evidence. "
    "Give band scores (0-9, halves allowed) for fluency, vocabulary, grammar, "
    "and pronunciation, one practical tip each, then an overall band. "
    "Keep it speakable: short sentences, no lists, markdown, or symbols."
)

IELTS_SCORE_PATTERNS = (
    "band score", "my score", "score me", "give me my scor",
    "how did i do", "assess me", "evaluate me", "my result",
)


def ielts_wants_scores(text):
    """True when the candidate asks for their scores (any wording)."""
    lowered = text.lower()
    return any(p in lowered for p in IELTS_SCORE_PATTERNS)


def ielts_director_note(user_turns):
    """Transient steering note for the reply following user turn N.

    The model knows the parts but not where it is; exact turn counts do.
    Returns None most turns so the examiner keeps its natural flow.
    """
    if user_turns == IELTS_PART1_END:
        return ("Director: Part 1 is complete. Now give Part 2: brief instructions, "
                "one cue-card topic, and invite the candidate to speak for 1-2 minutes.")
    if user_turns == IELTS_PART2_END:
        return ("Director: Part 2 is complete. Move to Part 3: discussion questions "
                "on the same theme, one per turn.")
    if user_turns == IELTS_WRAP_AT:
        return ("Director: wind down the test within 2 turns, then offer band scores "
                "with one tip per criterion.")
    return None
PRESETS = {"ielts": IELTS_EXAMINER_PROMPT}
PRESET_LANG = {"ielts": "en"}
# IELTS candidates pause to think mid-answer and speak 1-2 min in Part 2,
# so the preset tolerates longer pauses and much longer turns.
# Explicit --silence-ms / --max-utterance-s flags still win over these.
PRESET_ENDPOINT = {"ielts": {"silence_ms": 2500, "max_utterance_s": 120}}

VOICE_BANNER = {
    "th": "Loading speech models (MMS Thai TTS + Qwen3-ASR MLX)...",
    "en": "Loading speech models (Kokoro English TTS + Parakeet MLX STT)...",
}
VOICE_SUMMARY = {
    "th": ('สรุปบทสนทนาต่อไปนี้สั้นๆ ไม่เกิน 80 คำ เป็นภาษาไทย '
           'เน้นชื่อผู้ใช้ ความชอบ และเรื่องที่ค้างอยู่:\n'),
    "en": ('Summarize the following conversation briefly in English, '
           'max 80 words, keeping names, preferences, and open items:\n'),
}


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
    silence_ms: int = 800
    max_utterance_s: int = 15

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
            int(os.getenv("SILENCE_MS", "800")),
            int(os.getenv("MAX_UTTERANCE_S", "15")),
        )
