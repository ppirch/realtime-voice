"""Live STT backend: mlx-qwen3-asr with energy-based utterance endpointing.

The underlying model transcribes full utterances (no partial streaming),
so this backend accumulates mic chunks and finalizes on trailing silence:
speech >= ``min_speech_ms`` followed by ``silence_ms`` of quiet audio
emits one final event. Thresholds are guesses for a typical laptop mic;
tune per environment.
"""

import numpy as np

MODEL_SR = 16000


def endpoint_threshold(noise_floor):
    """Speech/silence boundary from measured room noise.

    Fixed guesses (e.g. 0.02) break on quiet mics, so scale from the
    actual floor with a sane minimum.
    """
    return max(noise_floor * 3, 0.008)


class Utterance:
    def __init__(self, text, is_final=True):
        self.text = text
        self.is_final = is_final


class Qwen3ASRMLXBackend:
    def __init__(self, model_id='Qwen/Qwen3-ASR-0.6B', language='Thai',
                 silence_rms=0.02, silence_ms=800, min_speech_ms=400,
                 max_utterance_s=15):
        from mlx_qwen3_asr import load_model
        self.model, _ = load_model(model_id)
        self.language = language
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
        from mlx_qwen3_asr import transcribe
        audio = np.concatenate(buf)
        res = transcribe(audio, model=self.model, language=self.language)
        return (res.text or '').strip()

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
