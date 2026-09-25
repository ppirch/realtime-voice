"""Session recording: transcript + audio persisted per run.

Enabled with ``--record DIR``. Layout per session::

    DIR/<timestamp>/transcript.md   # turns, appended live (crash-safe)
    DIR/<timestamp>/mic.wav         # user side, 16kHz mono
    DIR/<timestamp>/agent.wav       # TTS side, concatenated turn audio
    DIR/<timestamp>/meta.json       # settings, turn windows, latencies

Use as a context manager; files finalize on exit.
"""

import contextlib
import datetime
import json
import wave
from pathlib import Path

import numpy as np


class SessionRecorder:
    def __init__(self, root, sample_rate, lang, preset,
                 silence_ms, max_utterance_s):
        stamp = datetime.datetime.now().astimezone().strftime('%Y%m%d-%H%M%S')
        self.dir = Path(root) / stamp
        self.dir.mkdir(parents=True, exist_ok=False)
        self.sample_rate = sample_rate
        self._mic = bytearray()
        self._agent = []
        self._agent_sr = None
        self._turns = []
        self.meta = {
            'started': stamp, 'lang': lang, 'preset': preset,
            'silence_ms': silence_ms, 'max_utterance_s': max_utterance_s,
            'turns': self._turns,
        }
        self._md_path = self.dir / 'transcript.md'
        with open(self._md_path, 'w') as f:
            f.write(f'# Session {stamp} (lang={lang} preset={preset})\n\n')

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def mic_chunk(self, chunk):
        """Tap for the mic chunk stream; chunks are float32 mono."""
        x = np.asarray(chunk, dtype=np.float32).ravel()
        self._mic += (np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes()

    def turn(self, role, text, n=None, timings=None):
        """Append one transcript turn (role is 'user' or 'assistant')."""
        rec = {'role': role, 'text': text}
        if n is not None:
            rec['turn'] = n
        if timings is not None:
            rec.update(timings)
        self._turns.append(rec)
        who = 'You' if role == 'user' else 'Agent'
        with open(self._md_path, 'a') as f:
            f.write(f'## {who}' + (f' (turn {n})' if n else '') + '\n\n')
            f.write(text + '\n\n')
            if timings:
                f.write('<!-- ' + json.dumps(timings) + ' -->\n\n')

    def turn_window(self, n, t_start, t_end):
        """Wall-clock window of mic turn n (for aligning mic.wav)."""
        self._turns.append({'turn': n, 'mic_window': [t_start, t_end]})

    def agent_audio(self, arrays, sample_rate):
        self._agent_sr = sample_rate
        self._agent.extend([np.asarray(a, dtype=np.float32).ravel()
                            for a in arrays])

    def close(self):
        if self._mic:
            self._write_wav('mic.wav', bytes(self._mic), self.sample_rate)
        if self._agent:
            audio = np.concatenate(self._agent)
            self._write_wav('agent.wav',
                            (np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes(),
                            self._agent_sr)
        with open(self.dir / 'meta.json', 'w') as f:
            json.dump(self.meta, f, indent=1)

    def _write_wav(self, name, frames, sample_rate):
        with wave.open(str(self.dir / name), 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sample_rate)
            w.writeframes(frames)


def session_recorder(args, s, silence_ms, max_utterance_s):
    """SessionRecorder for --record DIR, else a null context yielding None."""
    if not args.record:
        return contextlib.nullcontext(None)
    return SessionRecorder(args.record, s.sample_rate, s.voice_lang,
                           args.preset, silence_ms, max_utterance_s)
