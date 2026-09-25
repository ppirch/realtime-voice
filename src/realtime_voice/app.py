import argparse
import contextlib
import os
import sys
import time
import warnings
from dataclasses import replace

os.environ.setdefault("HF_HUB_VERBOSITY", "error")

# Known-noisy third-party warnings (torch deprecations, HF anonymous
# rate-limit notice) — hidden for a clean voice-loop console.
warnings.filterwarnings(
    "ignore",
    message=".*(torch\\.jit\\.script|weight_norm|dropout option adds dropout|unauthenticated requests).*",
)

from .audio import Microphone, Speaker
from .config import VOICE_BANNER, VOICE_SUMMARY, Settings
from .history import ConversationHistory
from .llm import StreamingLLM
from .stt_endpoint import endpoint_threshold
from .stt_mlx import Qwen3ASRMLXBackend
from .stt_parakeet import ParakeetMLXBackend
from .text import sentence_chunks
from .tts_kokoro import KokoroTTS
from .tts_mms import MMSThaiTTS


def parse_args(argv=None):
    p = argparse.ArgumentParser(description='Realtime Thai voice conversation')
    p.add_argument('--text', action='store_true',
                   help='read user turns from stdin instead of the microphone')
    p.add_argument('--mute', action='store_true',
                   help='synthesize speech but skip speaker playback')
    p.add_argument('--max-turns', type=int, default=0,
                   help='stop after N turns (0 = unlimited)')
    p.add_argument('--stt-only', action='store_true',
                   help='microphone to text only, no LLM/TTS')
    p.add_argument('--lang', choices=('th', 'en'), default=None,
                   help='voice language backend (overrides VOICE_LANG)')
    p.add_argument('--system-prompt', default=None,
                   help='system prompt (overrides language default and env)')
    p.add_argument('--preset', choices=('ielts',), default=None,
                   help='built-in role preset (overrides language default)')
    p.add_argument('--silence-ms', type=int, default=None,
                   help='trailing silence to end a turn (default 800, ielts 2500)')
    p.add_argument('--max-utterance-s', type=int, default=None,
                   help='longest single turn in seconds (default 15, ielts 120)')
    p.add_argument('--live', action='store_true',
                   help='live word previews while speaking (mlx-whisper streaming, needs stt-live extra)')
    return p.parse_args(argv)


def resolve_lang_prompt(args, s):
    """CLI > explicit lang default > env (.env) > built-in default."""
    from .config import EN_SYSTEM_PROMPT, PRESET_LANG, PRESETS, TH_SYSTEM_PROMPT
    if args.system_prompt:
        return (args.lang or s.voice_lang), args.system_prompt
    if args.preset:
        return (args.lang or PRESET_LANG.get(args.preset) or s.voice_lang), PRESETS[args.preset]
    if args.lang:
        lang = args.lang
        prompt = EN_SYSTEM_PROMPT if lang == "en" else TH_SYSTEM_PROMPT
        return lang, prompt
    return s.voice_lang, s.system_prompt


def resolve_endpoint(args, s):
    """Explicit flag > preset default > env (.env) > built-in default."""
    from .config import PRESET_ENDPOINT
    preset = PRESET_ENDPOINT.get(args.preset or "", {})
    silence_ms = (args.silence_ms if args.silence_ms is not None
                  else preset.get("silence_ms", s.silence_ms))
    max_utterance_s = (args.max_utterance_s if args.max_utterance_s is not None
                       else preset.get("max_utterance_s", s.max_utterance_s))
    return silence_ms, max_utterance_s


def mic_texts(backend, mic, sample_rate, on_preview=None):
    for event in backend.stream(mic.chunks(), sample_rate=sample_rate):
        if not event.text.strip():
            continue
        if getattr(event, 'is_final', True):
            yield event.text.strip()
        elif on_preview is not None:
            on_preview(event.text.strip())


def show_preview(text):
    """One-line rolling caption on stderr; cleared when the turn lands."""
    print(f"\r\x1b[K… {text}", end="", file=sys.stderr, flush=True)


def clear_preview():
    print("\r\x1b[K", end="", file=sys.stderr, flush=True)


@contextlib.contextmanager
def mic_session(args, s, backend_cls):
    """Mic + calibrated backend. Owns setup; the caller runs the turns."""
    silence_ms, max_utterance_s = resolve_endpoint(args, s)
    with Microphone(s.sample_rate, s.input_chunk_ms,
                     qsize=200 if args.live else 32) as mic:
        floor = mic_check(mic)
        threshold = endpoint_threshold(floor)
        print(f"endpoint threshold: {threshold:.3f}",
              file=sys.stderr, flush=True)
        backend = build_backend(args, s, backend_cls, threshold,
                                silence_ms, max_utterance_s)
        if args.live:
            print("live captions on — words appear as you speak",
                  file=sys.stderr, flush=True)
        yield backend, mic, silence_ms


def run_mic_loop(args, backend, mic, sample_rate, silence_ms,
                 on_turn, settle, on_preview=None):
    """Shared turn loop: previews, dispatch, optional half-duplex settle.

    settle (sleep + flush) exists because the mic hears our own speaker;
    only the speaking loop needs it.
    """
    if on_preview is None:
        on_preview = show_preview if args.live else None
    print(listening_msg(silence_ms), file=sys.stderr, flush=True)
    n = 0
    for text in mic_texts(backend, mic, sample_rate, on_preview=on_preview):
        clear_preview()
        n += 1
        on_turn(text, n)
        if args.max_turns and n >= args.max_turns:
            break
        if settle:
            # Half-duplex: let the reverb tail arrive, then drop it.
            time.sleep(0.4)
            mic.flush()
        print(listening_msg(silence_ms), file=sys.stderr, flush=True)
    return n


def build_voice(s):
    """STT adapter class + TTS factory for a language. One row per lang.

    TTS is a factory (not an instance) so --stt-only never loads voices.
    """
    if s.voice_lang == "en":
        return ParakeetMLXBackend, KokoroTTS
    return Qwen3ASRMLXBackend, MMSThaiTTS


def build_backend(args, s, backend_cls, threshold, silence_ms, max_utterance_s):
    """Live streaming backend (--live) or the default utterance backend."""
    if args.live:
        from .stt_live import LiveWhisperMLXBackend
        return LiveWhisperMLXBackend(
            language=s.voice_lang,
            silence_rms=threshold, silence_ms=silence_ms,
            max_utterance_s=max_utterance_s)
    return backend_cls(
        silence_rms=threshold, silence_ms=silence_ms,
        max_utterance_s=max_utterance_s)


def mic_check(mic):
    """Print input device + live level, return measured noise floor.

    Asks the user to speak during the ~2s window; buffered audio stays
    queued (maxsize 32 ≈ 2.5s), so nothing said is lost.
    """
    import statistics
    print(f"mic: {mic.device_name()} — say a few words now...",
          file=sys.stderr, flush=True)
    time.sleep(2.0)
    peak = mic.level()
    floor = statistics.median(mic.levels) if mic.levels else 0.0
    ok = peak >= max(floor * 4, 0.006)
    print(f"mic level: {peak:.3f} (room {floor:.3f}) " + ("(ok)" if ok
          else "(SILENT — check macOS Microphone permission for your terminal)"),
          file=sys.stderr, flush=True)
    return floor


LISTENING_MSG = "[listening — speak, then pause ~{pause}s to send]"


def listening_msg(silence_ms):
    return LISTENING_MSG.format(pause=f"{silence_ms / 1000:g}")


def stdin_texts():
    while True:
        print("> ", file=sys.stderr, end="", flush=True)
        line = sys.stdin.readline()
        if not line:
            break
        if line.strip():
            yield line.strip()


def main(argv=None):
    args = parse_args(argv)
    s = Settings.from_env()
    voice_lang, system_prompt = resolve_lang_prompt(args, s)
    s = replace(s, voice_lang=voice_lang, system_prompt=system_prompt)

    if args.stt_only:
        backend_cls, _ = build_voice(s)
        silence_ms, _ = resolve_endpoint(args, s)
        print(f"STT-only mode — speak, pause ~{silence_ms / 1000:g}s to finalize, Ctrl-C to quit",
              file=sys.stderr)
        with mic_session(args, s, backend_cls) as (backend, mic, silence_ms):
            run_mic_loop(args, backend, mic, s.sample_rate, silence_ms,
                         on_turn=lambda text, n: print(text, flush=True),
                         settle=False)
        return

    if not s.llm_model:
        raise SystemExit("Set LLM_MODEL in .env")

    llm = StreamingLLM(
        s.llm_base_url,
        s.llm_api_key,
        s.llm_model,
        s.system_prompt,
        protocol=s.llm_protocol,
        max_tokens=s.max_tokens,
        reasoning_effort=s.reasoning_effort or None,
    )
    print(VOICE_BANNER[s.voice_lang], file=sys.stderr, flush=True)
    backend_cls, tts_factory = build_voice(s)
    tts = tts_factory()
    summarize_instruction = VOICE_SUMMARY[s.voice_lang]
    speaker = None if args.mute else Speaker(s.tts_sample_rate)
    history = ConversationHistory(max_recent=8)

    def summarize_older(msgs):
        joined = '\n'.join(f"{m['role']}: {m['content']}" for m in msgs)
        prompt = summarize_instruction + joined
        return ''.join(llm.stream([{'role': 'user', 'content': prompt}]))

    def handle_turn(text, n):
        print(f"You: {text}", flush=True)
        history.add("user", text)
        t0 = time.time()
        first, synth_total, n_chunks = -1.0, 0.0, 0
        answer = ""
        print("Agent: ", end="", flush=True)
        for chunk in sentence_chunks(llm.stream(history.build(summarize=summarize_older))):
            if first < 0:
                first = time.time() - t0
            print(chunk, end="", flush=True)
            answer += chunk
            t1 = time.time()
            audio = tts.synthesize(chunk)
            synth_total += time.time() - t1
            n_chunks += 1
            if speaker is not None:
                speaker.play(audio)
        print(flush=True)
        history.add("assistant", answer)
        total = time.time() - t0
        print(f"[turn {n}] first-audio {first:.1f}s | {n_chunks} chunks | "
              f"synth {synth_total:.1f}s | total {total:.1f}s",
              file=sys.stderr, flush=True)
        return answer.strip() != ""

    print("Realtime Voice — Ctrl-C to quit", file=sys.stderr)
    n = 0
    if args.text:
        source = stdin_texts()
        for text in source:
            n += 1
            handle_turn(text, n)
            if args.max_turns and n >= args.max_turns:
                break
    else:
        with mic_session(args, s, backend_cls) as (backend, mic, silence_ms):
            run_mic_loop(args, backend, mic, s.sample_rate, silence_ms,
                         on_turn=lambda text, n: handle_turn(text, n),
                         settle=True)
