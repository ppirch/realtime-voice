"""Local English TTS backend using Kokoro-82M (native 24 kHz output).

Needs the espeak-ng system package (``brew install espeak-ng``).
Weights download from HuggingFace Hub on first use (~300 MB).
"""

import numpy as np

TARGET_SR = 24000


class KokoroTTS:
    def __init__(self, lang_code='a', voice='af_heart'):
        from kokoro import KPipeline
        self.voice = voice
        self.pipeline = KPipeline(lang_code=lang_code)

    def synthesize(self, text):
        if not text or not text.strip():
            return np.zeros(int(TARGET_SR * 0.1), dtype=np.float32)
        segs = [np.asarray(a, dtype=np.float32)
                for _, _, a in self.pipeline(text, voice=self.voice)]
        if not segs:
            return np.zeros(int(TARGET_SR * 0.1), dtype=np.float32)
        return np.concatenate(segs).astype(np.float32)
