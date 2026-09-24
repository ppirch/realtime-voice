import numpy as np
class FastThaiG2PKokoro:
    def __init__(self, backend=None): self.backend = backend
    def synthesize(self, text):
        if self.backend is None:
            raise RuntimeError('Configure the FastThaiG2P + Thai Kokoro backend before running live mode.')
        return np.asarray(self.backend.synthesize(text), dtype=np.float32)
