"""Local text to speech: text in, speech out, no API needed.

Uses the same local backends as the voice loop (Kokoro-82M for English,
MMS Thai for Thai) and streams chunk by chunk so the first audio plays
before the rest is synthesized.
"""

import argparse
import sys
import time
import wave

import numpy as np

from .audio import Speaker
from .text import sentence_chunks

SAMPLE_RATE = 24000


def build_tts(lang):
    """Local TTS backend for a language. Imported lazily so --help works
    without the heavy extras installed."""
    if lang == "en":
        try:
            from .tts_kokoro import KokoroTTS
        except ImportError:
            raise SystemExit("English TTS needs '.[tts-en]' and espeak-ng")
        return KokoroTTS()
    try:
        from .tts_mms import MMSThaiTTS
    except ImportError:
        raise SystemExit("Thai TTS needs '.[tts-local]'")
    return MMSThaiTTS()


def parse_args(argv=None):
    p = argparse.ArgumentParser(description='Local text to speech (no API key needed)')
    p.add_argument('text', nargs='?', default=None,
                   help='text to speak (reads stdin when omitted)')
    p.add_argument('--lang', choices=('th', 'en'), default='th',
                   help='speech backend (default th)')
    p.add_argument('--out', default=None, metavar='WAV',
                   help='also save the audio to a WAV file')
    p.add_argument('--mute', action='store_true',
                   help='skip speaker playback (needs --out)')
    p.add_argument('--listen', action='store_true',
                   help='daemon mode: load the model once, speak every stdin line until EOF')
    return p.parse_args(argv)


def speak(text, lang='th', out=None, mute=False, tts=None, speaker=None):
    """Synthesize chunk by chunk; play each as soon as ready.

    Returns the concatenated audio (float32, 24 kHz mono).
    """
    if mute and out is None:
        raise SystemExit("--mute needs --out, otherwise nothing happens")
    tts = tts or build_tts(lang)
    spk = None if mute else (speaker or Speaker(SAMPLE_RATE))
    t0, first = time.time(), -1.0
    audios = []
    for chunk in sentence_chunks(iter([text or ''])):
        audio = np.asarray(tts.synthesize(chunk), dtype=np.float32)
        audios.append(audio)
        if spk is not None:
            if first < 0:
                first = time.time() - t0
            spk.play(audio)
    full = np.concatenate(audios) if audios else np.zeros(0, dtype=np.float32)
    if out is not None:
        write_wav(out, full)
    timing = f"{len(audios)} chunks | total {time.time() - t0:.1f}s"
    if not mute:
        timing = f"first-audio {max(first, 0.0):.1f}s | " + timing
    print(f"[say] {timing}", file=sys.stderr, flush=True)
    return full


def write_wav(path, audio):
    pcm = np.clip(np.asarray(audio, dtype=np.float32), -1.0, 1.0)
    with wave.open(path, 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes((pcm * 32767).astype(np.int16).tobytes())


def run_daemon(tts, speaker):
    """Speak every stdin line until EOF. The model stays loaded between
    lines, so per-message cost is synth only (~0.3-0.6s), not reload."""
    for line in sys.stdin:
        if line.strip():
            speak(line.strip(), tts=tts, speaker=speaker)


def main(argv=None):
    args = parse_args(argv)
    if args.listen:
        if args.text is not None or args.out is not None or args.mute:
            raise SystemExit("--listen takes no TEXT/--out/--mute")
        run_daemon(build_tts(args.lang), Speaker(SAMPLE_RATE))
        return
    text = args.text
    if text is None:
        text = sys.stdin.read().strip()
    if not text:
        raise SystemExit("nothing to speak: pass TEXT or pipe stdin")
    speak(text, lang=args.lang, out=args.out, mute=args.mute)
