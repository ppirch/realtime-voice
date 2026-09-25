"""Shared utterance-endpointing core for all STT adapters.

Every adapter answers the same question — "has the user finished their
turn?" — from mic-chunk energy. This module owns that decision plus the
chunk↔turn plumbing (resampling, the turn loop, the Utterance protocol),
so adapters only implement transcription.
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


def resample(chunk, sample_rate):
    """Mic chunk -> float32 mono at MODEL_SR."""
    x = np.asarray(chunk, dtype=np.float32).ravel()
    if sample_rate == MODEL_SR:
        return x
    n = int(len(x) * MODEL_SR / sample_rate)
    return np.interp(np.arange(n),
                     np.arange(len(x)) * (MODEL_SR / sample_rate), x).astype(np.float32)


class Endpointer:
    """Energy-based turn detector: speech then trailing silence, or cap."""

    def __init__(self, silence_rms=0.02, silence_ms=800, min_speech_ms=400,
                 max_utterance_s=15):
        self.silence_rms = silence_rms
        self.silence_ms = silence_ms
        self.min_speech_ms = min_speech_ms
        self.max_utterance_s = max_utterance_s
        self.reset()

    def reset(self):
        self.speech_ms, self.silent_ms, self.total_s = 0.0, 0.0, 0.0

    def is_speech(self, x):
        return float(np.sqrt((x ** 2).mean())) >= self.silence_rms

    def feed(self, x):
        """Consume one MODEL_SR chunk; True when the turn is complete."""
        dur_ms = len(x) / MODEL_SR * 1000
        self.total_s += dur_ms / 1000
        if self.is_speech(x):
            self.speech_ms += dur_ms
            self.silent_ms = 0.0
        else:
            self.silent_ms += dur_ms
        done = (self.speech_ms >= self.min_speech_ms
                and self.silent_ms >= self.silence_ms)
        return done or (self.total_s >= self.max_utterance_s
                        and self.speech_ms >= self.min_speech_ms)


def utterance_stream(audio_chunks, sample_rate, endpoint, transcribe):
    """Accumulate chunks, decode each completed turn, yield final Utterances."""
    buf = []
    for chunk in audio_chunks:
        x = resample(chunk, sample_rate)
        buf.append(x)
        if endpoint.feed(x):
            text = transcribe(buf)
            buf = []
            endpoint.reset()
            if text and text.strip():
                yield Utterance(text.strip())
