class Qwen3ASRStreaming:
    def __init__(self, backend=None): self.backend = backend
    def stream(self, audio_chunks, sample_rate):
        if self.backend is None:
            raise RuntimeError('Configure the MLX Qwen3-ASR streaming backend before running live mode.')
        return self.backend.stream(audio_chunks, sample_rate=sample_rate)
