"""Live STT backend: Parakeet-TDT (MLX) with energy-based endpointing.

Same utterance protocol as the Qwen3 backend: accumulate mic chunks,
finalize on trailing silence, transcribe the utterance from a temp WAV
(Parakeet takes file paths). English-first model.
"""

import os
import tempfile
import wave

import numpy as np

from .stt_mlx import MODEL_SR, Utterance


class ParakeetMLXBackend:
    def __init__(self, model_id='mlx-community/parakeet-tdt-0.6b-v2',
                 silence_rms=0.02, silence_ms=800, min_speech_ms=400,
                 max_utterance_s=15):
        from parakeet_mlx import from_pretrained
        self.model = from_pretrained(model_id)
        self.silence_rms = silence_rms
        self.silence_ms = silence_ms
        self.min_speech_ms = min_speech_ms
        self.max_utterance_s = max_utterance_s

    def _resample(self, chunk, sample_rate):
        x = np.asarray(chunk, dtype=np.float32).ravel()
        if sample_rate == MODEL_SR:
            return x
        n = int(len(x) * MODEL_SR / sample_rate)
        return np.interp(np.arange(n),
                         np.arange(len(x)) * (MODEL_SR / sample_rate), x).astype(np.float32)

    def _transcribe(self, buf):
        audio = np.concatenate(buf)
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            path = f.name
        try:
            with wave.open(path, 'wb') as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(MODEL_SR)
                w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
            return (self.model.transcribe(path).text or '').strip()
        finally:
            os.unlink(path)

    def stream(self, audio_chunks, sample_rate=16000):
        buf, speech_ms, silent_ms = [], 0.0, 0.0
        for chunk in audio_chunks:
            x = self._resample(chunk, sample_rate)
            dur_ms = len(x) / MODEL_SR * 1000
            buf.append(x)
            if float(np.sqrt((x ** 2).mean())) >= self.silence_rms:
                speech_ms += dur_ms
                silent_ms = 0.0
            else:
                silent_ms += dur_ms
            total_s = sum(len(b) for b in buf) / MODEL_SR
            done = (speech_ms >= self.min_speech_ms and silent_ms >= self.silence_ms)
            done = done or (total_s >= self.max_utterance_s and speech_ms >= self.min_speech_ms)
            if done:
                text = self._transcribe(buf)
                buf, speech_ms, silent_ms = [], 0.0, 0.0
                if text:
                    yield Utterance(text)
