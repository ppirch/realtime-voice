"""Live STT backend: mlx-whisper with streaming word previews.

Unlike the utterance backends (which emit one final event per turn), this
yields interim ``Utterance(text, is_final=False)`` previews while the user
speaks, then one final event at the silence endpoint.

Streaming policy (prefix confirmation via HypothesisBuffer) adapted from
ufal/whisper_streaming (MIT licence); the MLX transcribe call mirrors its
MLXWhisper backend. No dependency on that repo: it has no PyPI package,
and we only need the buffer logic plus one transcribe call.
"""

import numpy as np

from .stt_mlx import MODEL_SR, Utterance

MODEL_ID = 'mlx-community/whisper-large-v3-turbo'
LIVE_EVERY_S = 2.0  # re-decode cadence while speech is arriving
TRIM_S = 10.0  # decode window cap; keeps each iteration ~1-2s on M-series


class HypothesisBuffer:
    """Confirm only the word prefix two consecutive decodes agree on."""

    def __init__(self):
        self.commited_in_buffer = []
        self.buffer = []
        self.new = []
        self.last_commited_time = 0.0

    def insert(self, new, offset):
        new = [(a + offset, b + offset, t) for a, b, t in new]
        self.new = [(a, b, t) for a, b, t in new
                    if a > self.last_commited_time - 0.1]
        if len(self.new) >= 1:
            a, b, t = self.new[0]
            if abs(a - self.last_commited_time) < 1 and self.commited_in_buffer:
                cn, nn = len(self.commited_in_buffer), len(self.new)
                for i in range(1, min(min(cn, nn), 5) + 1):
                    c = " ".join(self.commited_in_buffer[-j][2]
                                 for j in range(1, i + 1)[::-1])
                    tail = " ".join(self.new[j - 1][2] for j in range(1, i + 1))
                    if c == tail:
                        del self.new[:i]
                        break

    def flush(self):
        commit = []
        while self.new:
            na, nb, nt = self.new[0]
            if not self.buffer:
                break
            if nt == self.buffer[0][2]:
                commit.append((na, nb, nt))
                self.last_commited_time = nb
                self.buffer.pop(0)
                self.new.pop(0)
            else:
                break
        self.buffer = self.new
        self.new = []
        self.commited_in_buffer.extend(commit)
        return commit

    def complete(self):
        return self.buffer


class MLXTranscriber:
    """Thin wrapper over mlx_whisper returning [(start, end, word)]."""

    def __init__(self, model_id=MODEL_ID, language='th'):
        from mlx_whisper.transcribe import ModelHolder, transcribe
        import mlx.core as mx
        ModelHolder.get_model(model_id, mx.float16)
        self._transcribe = transcribe
        self.model_id, self.language = model_id, language
        # First call compiles kernels; don't stall the first turn on it.
        self.transcribe(np.zeros(MODEL_SR, dtype=np.float32))

    def transcribe(self, audio):
        res = self._transcribe(
            np.asarray(audio, dtype=np.float32), language=self.language,
            word_timestamps=True, condition_on_previous_text=True,
            path_or_hf_repo=self.model_id)
        words = []
        for seg in res.get('segments', []):
            if seg.get('no_speech_prob', 0) > 0.9:
                continue
            for w in seg.get('words', []):
                words.append((w['start'], w['end'], w['word']))
        return words


class LiveWhisperMLXBackend:
    def __init__(self, model_id=MODEL_ID, language='th', live_every_s=LIVE_EVERY_S,
                 trim_s=TRIM_S, silence_rms=0.02, silence_ms=800,
                 min_speech_ms=400, max_utterance_s=120, transcriber=None):
        self.language = language
        self.transcriber = transcriber or MLXTranscriber(model_id, language)
        self.live_every_s = live_every_s
        self.trim_s = trim_s
        self.silence_rms = silence_rms
        self.silence_ms = silence_ms
        self.min_speech_ms = min_speech_ms
        self.max_utterance_s = max_utterance_s

    def _decode(self, hb, buf, offset):
        try:
            words = self.transcriber.transcribe(buf)
        except AssertionError:
            return []  # transient garbage window; next tick heals
        hb.insert(words, offset)
        return hb.flush()

    def stream(self, audio_chunks, sample_rate=16000):
        buf = np.array([], dtype=np.float32)
        offset = 0.0
        hb, parts = HypothesisBuffer(), []
        speech_ms, silent_ms, turn_s = 0.0, 0.0, 0.0
        since_tick, speech_since_tick = 0.0, False
        last_preview = ""

        def preview():
            # Words carry their own spacing (" world", "สวัสดี"); joining
            # with " " would double-space English and shred Thai fragments.
            tail = "".join(t for _, _, t in hb.complete())
            return ("".join(parts) + tail).strip()

        for chunk in audio_chunks:
            x = np.asarray(chunk, dtype=np.float32).ravel()
            if sample_rate != MODEL_SR:
                n = int(len(x) * MODEL_SR / sample_rate)
                x = np.interp(np.arange(n),
                              np.arange(len(x)) * (MODEL_SR / sample_rate),
                              x).astype(np.float32)
            dur_ms = len(x) / MODEL_SR * 1000
            buf = np.append(buf, x)
            turn_s += dur_ms / 1000
            if float(np.sqrt((x ** 2).mean())) >= self.silence_rms:
                speech_ms += dur_ms
                silent_ms = 0.0
                speech_since_tick = True
            else:
                silent_ms += dur_ms
            since_tick += dur_ms / 1000

            # Trim the decode window so each iteration stays ~1-2s; confirmed
            # text already lives in parts. Prefer a committed word boundary;
            # fall back to a hard cut (the hypothesis buffer self-heals).
            if len(buf) / MODEL_SR > self.trim_s + self.live_every_s:
                horizon = offset + len(buf) / MODEL_SR - self.trim_s
                committed = [b for _, b, _ in hb.commited_in_buffer if b <= horizon]
                cut = max(committed) if committed else horizon
                if cut > offset:
                    buf = buf[int((cut - offset) * MODEL_SR):]
                    offset = cut

            if (speech_ms >= self.min_speech_ms and speech_since_tick
                    and since_tick >= self.live_every_s
                    and turn_s < self.max_utterance_s):
                for _, _, t in self._decode(hb, buf, offset):
                    parts.append(t)
                since_tick, speech_since_tick = 0.0, False
                text = preview()
                if text and text != last_preview:
                    last_preview = text
                    yield Utterance(text, is_final=False)

            done = (speech_ms >= self.min_speech_ms and silent_ms >= self.silence_ms)
            done = done or (turn_s >= self.max_utterance_s
                            and speech_ms >= self.min_speech_ms)
            if done:
                for _, _, t in self._decode(hb, buf, offset):
                    parts.append(t)
                text = preview()
                offset += len(buf) / MODEL_SR
                buf = np.array([], dtype=np.float32)
                hb, parts = HypothesisBuffer(), []
                speech_ms, silent_ms, turn_s = 0.0, 0.0, 0.0
                since_tick, speech_since_tick = 0.0, False
                last_preview = ""
                if text:
                    yield Utterance(text, is_final=True)
