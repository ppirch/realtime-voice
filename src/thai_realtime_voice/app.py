import argparse
import sys
import time
import warnings
from dataclasses import replace

# Known-noisy third-party warnings (torch deprecations, HF anonymous
# rate-limit notice) — hidden for a clean voice-loop console.
warnings.filterwarnings(
    "ignore",
    message=".*(torch\\.jit\\.script|weight_norm|dropout option adds dropout|unauthenticated requests).*",
)

from .config import Settings
from .audio import Microphone, Speaker
from .history import ConversationHistory
from .llm import StreamingLLM
from .stt import Qwen3ASRStreaming
from .stt_mlx import Qwen3ASRMLXBackend
from .stt_parakeet import ParakeetMLXBackend
from .tts_mms import MMSThaiTTS
from .tts_kokoro import KokoroTTS
from .text import sentence_chunks


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
    return p.parse_args(argv)


def resolve_lang_prompt(args, s):
    """CLI > explicit lang default > env (.env) > built-in default."""
    from .config import EN_SYSTEM_PROMPT, TH_SYSTEM_PROMPT
    if args.system_prompt:
        return (args.lang or s.voice_lang), args.system_prompt
    if args.lang:
        lang = args.lang
        prompt = EN_SYSTEM_PROMPT if lang == "en" else TH_SYSTEM_PROMPT
        return lang, prompt
    return s.voice_lang, s.system_prompt


def mic_texts(asr, mic, sample_rate):
    for event in asr.stream(mic.chunks(), sample_rate=sample_rate):
        if getattr(event, 'is_final', False) and event.text.strip():
            yield event.text.strip()


def stdin_texts():
    for line in sys.stdin:
        if line.strip():
            yield line.strip()


def main(argv=None):
    args = parse_args(argv)
    s = Settings.from_env()
    voice_lang, system_prompt = resolve_lang_prompt(args, s)
    s = replace(s, voice_lang=voice_lang, system_prompt=system_prompt)

    if args.stt_only:
        backend = ParakeetMLXBackend() if s.voice_lang == "en" else Qwen3ASRMLXBackend()
        asr = Qwen3ASRStreaming(backend=backend)
        print("STT-only mode — speak, pause ~1s to finalize, Ctrl-C to quit",
              file=sys.stderr)
        with Microphone(s.sample_rate, s.input_chunk_ms) as mic:
            for text in mic_texts(asr, mic, s.sample_rate):
                print(text, flush=True)
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
    if s.voice_lang == "en":
        print("Loading speech models (Kokoro English TTS + Parakeet MLX STT)...",
              file=sys.stderr, flush=True)
        asr = Qwen3ASRStreaming(backend=ParakeetMLXBackend())
        tts = KokoroTTS()
        summarize_instruction = (
            'Summarize the following conversation briefly in English, '
            'max 80 words, keeping names, preferences, and open items:\n'
        )
    else:
        print("Loading speech models (MMS Thai TTS + Qwen3-ASR MLX)...",
              file=sys.stderr, flush=True)
        asr = Qwen3ASRStreaming(backend=Qwen3ASRMLXBackend())
        tts = MMSThaiTTS()
        summarize_instruction = (
            'สรุปบทสนทนาต่อไปนี้สั้นๆ ไม่เกิน 80 คำ เป็นภาษาไทย '
            'เน้นชื่อผู้ใช้ ความชอบ และเรื่องที่ค้างอยู่:\n'
        )
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

    print("Thai Realtime Voice — Ctrl-C to quit", file=sys.stderr)
    n = 0
    if args.text:
        source = stdin_texts()
        for text in source:
            n += 1
            handle_turn(text, n)
            if args.max_turns and n >= args.max_turns:
                break
    else:
        with Microphone(s.sample_rate, s.input_chunk_ms) as mic:
            for text in mic_texts(asr, mic, s.sample_rate):
                n += 1
                handle_turn(text, n)
                if args.max_turns and n >= args.max_turns:
                    break
                # Half-duplex: the mic hears our own speaker during playback.
                # Let the reverb tail arrive, then drop it before listening.
                time.sleep(0.4)
                mic.flush()
