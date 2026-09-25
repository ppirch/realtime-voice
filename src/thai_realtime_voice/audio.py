import queue
import threading
import numpy as np
try:
    import sounddevice as sd
except ImportError:
    sd = None

class Microphone:
    def __init__(self, sample_rate=16000, chunk_ms=80):
        if sd is None: raise RuntimeError('Install sounddevice: pip install sounddevice')
        self.sample_rate, self.chunk_ms = sample_rate, chunk_ms
        self.q = queue.Queue(maxsize=32)
        self.stream = None
    def _cb(self, indata, frames, time_info, status):
        del frames, time_info, status
        chunk = np.asarray(indata[:,0], dtype=np.float32).copy()
        try: self.q.put_nowait(chunk)
        except queue.Full:
            try: self.q.get_nowait()
            except queue.Empty: pass
            self.q.put_nowait(chunk)
    def __enter__(self):
        self.stream = sd.InputStream(samplerate=self.sample_rate, channels=1, dtype='float32', blocksize=int(self.sample_rate*self.chunk_ms/1000), callback=self._cb)
        self.stream.start(); return self
    def __exit__(self, *args):
        if self.stream: self.stream.stop(); self.stream.close()
    def chunks(self):
        while True: yield self.q.get()
    def flush(self):
        """Drop everything captured so far (e.g. the speaker's own echo)."""
        while True:
            try: self.q.get_nowait()
            except queue.Empty: break

class Speaker:
    def __init__(self, sample_rate=24000):
        if sd is None: raise RuntimeError('Install sounddevice: pip install sounddevice')
        self.sample_rate = sample_rate
    def stop(self):
        sd.stop()
    def play(self, audio):
        sd.play(np.asarray(audio, dtype=np.float32), self.sample_rate, blocking=True)
