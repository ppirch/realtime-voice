from dataclasses import dataclass
import os
from dotenv import load_dotenv

@dataclass(frozen=True)
class Settings:
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    system_prompt: str
    sample_rate: int = 16000
    input_chunk_ms: int = 80
    tts_sample_rate: int = 24000

    @classmethod
    def from_env(cls):
        load_dotenv()
        return cls(
            os.getenv('LLM_BASE_URL', 'http://localhost:8000/v1').rstrip('/'),
            os.getenv('LLM_API_KEY', ''),
            os.getenv('LLM_MODEL', ''),
            os.getenv('LLM_SYSTEM_PROMPT', 'You are a concise helpful Thai voice assistant. Reply naturally in Thai unless the user asks for another language.'),
            int(os.getenv('SAMPLE_RATE', '16000')),
            int(os.getenv('INPUT_CHUNK_MS', '80')),
            int(os.getenv('TTS_SAMPLE_RATE', '24000')),
        )
