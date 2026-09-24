"""Local Thai TTS backend using facebook/mms-tts-tha (VITS, CPU/MPS).

Outputs 24 kHz mono float32 to match ``SAMPLE_RATE``/``Speaker``.
Model weights download from HuggingFace Hub on first use (~40 MB).
"""

import numpy as np
import sys

TARGET_SR = 24000


class MMSThaiTTS:
    def __init__(self, model_id='facebook/mms-tts-tha', device=None):
        import torch
        from transformers import AutoTokenizer, VitsModel

        self._torch = torch
        self.device = device or ('mps' if torch.backends.mps.is_available() else 'cpu')
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = VitsModel.from_pretrained(model_id).to(self.device).eval()
        self.model_sr = self.model.config.sampling_rate

    def synthesize(self, text):
        if not text or not text.strip():
            return np.zeros(int(TARGET_SR * 0.1), dtype=np.float32)
        try:
            ids = self.tokenizer(text, return_tensors='pt').to(self.device)
            with self._torch.no_grad():
                wav = self.model(**ids).waveform.cpu().numpy().squeeze().astype(np.float32)
        except RuntimeError as e:
            # Degenerate token sequence (e.g. non-Thai-only input like
            # 'Sure!'): VITS attention overflows. Degrade to silence
            # instead of crashing the voice loop.
            print(f'MMSThaiTTS: skipping unspeakable chunk {text!r:.40}: {e}',
                  file=sys.stderr)
            return np.zeros(int(TARGET_SR * 0.1), dtype=np.float32)
        if self.model_sr != TARGET_SR:
            n = int(len(wav) * TARGET_SR / self.model_sr)
            wav = np.interp(
                np.arange(n),
                np.arange(len(wav)) * (TARGET_SR / self.model_sr),
                wav,
            ).astype(np.float32)
        return wav
