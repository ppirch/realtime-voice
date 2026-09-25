"""STT adapter: mlx-qwen3-asr transcribes turns found by the shared endpointer."""

from .stt_endpoint import (
    MODEL_SR,
    Endpointer,
    Utterance,
    endpoint_threshold,
    utterance_stream,
)

__all__ = ["MODEL_SR", "Qwen3ASRMLXBackend", "Utterance", "endpoint_threshold"]


class QwenTranscriber:
    """Turn audio (list of MODEL_SR chunks) -> text. Weights load here."""

    def __init__(self, model_id='Qwen/Qwen3-ASR-0.6B', language='Thai'):
        from mlx_qwen3_asr import load_model
        self.model, _ = load_model(model_id)
        self.language = language

    def __call__(self, buf):
        import numpy as np
        from mlx_qwen3_asr import transcribe
        audio = np.concatenate(buf)
        res = transcribe(audio, model=self.model, language=self.language)
        return (res.text or '').strip()


class Qwen3ASRMLXBackend:
    def __init__(self, model_id='Qwen/Qwen3-ASR-0.6B', language='Thai',
                 silence_rms=0.02, silence_ms=800, min_speech_ms=400,
                 max_utterance_s=15, transcriber=None):
        self.transcriber = transcriber or QwenTranscriber(model_id, language)
        self.endpoint = Endpointer(silence_rms, silence_ms,
                                   min_speech_ms, max_utterance_s)

    def stream(self, audio_chunks, sample_rate=16000):
        yield from utterance_stream(audio_chunks, sample_rate,
                                    self.endpoint, self.transcriber)
