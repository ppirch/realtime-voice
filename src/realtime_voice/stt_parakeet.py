"""STT adapter: Parakeet-TDT (MLX) transcribes turns found by the shared endpointer.

Same utterance protocol as the Qwen3 adapter; only transcription differs
(Parakeet takes file paths, so each turn goes through a temp WAV).
English-first model.
"""

import os
import tempfile
import wave

import numpy as np

from .stt_endpoint import MODEL_SR, Endpointer, utterance_stream


class ParakeetTranscriber:
    """Turn audio (list of MODEL_SR chunks) -> text. Weights load here."""

    def __init__(self, model_id='mlx-community/parakeet-tdt-0.6b-v2'):
        from parakeet_mlx import from_pretrained
        self.model = from_pretrained(model_id)

    def __call__(self, buf):
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


class ParakeetMLXBackend:
    def __init__(self, model_id='mlx-community/parakeet-tdt-0.6b-v2',
                 silence_rms=0.02, silence_ms=800, min_speech_ms=400,
                 max_utterance_s=15, transcriber=None):
        self.transcriber = transcriber or ParakeetTranscriber(model_id)
        self.endpoint = Endpointer(silence_rms, silence_ms,
                                   min_speech_ms, max_utterance_s)

    def stream(self, audio_chunks, sample_rate=16000):
        yield from utterance_stream(audio_chunks, sample_rate,
                                    self.endpoint, self.transcriber)
