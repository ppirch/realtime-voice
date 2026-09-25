# Realtime Voice

Realtime voice conversation on Apple Silicon, in Thai (default) and English (`--lang en`).

Pipeline: microphone -> local streaming STT -> streaming LLM API -> local TTS -> speaker.

## LLM: OpenCode Zen / Space Bunny Free

The default configuration is:

- model: `space-bunny-free` (free, unlimited promo quota)
- endpoint: `https://opencode.ai/zen/go/v1/chat/completions`
- protocol: OpenAI Chat Completions API (`choices[].delta.content` stream)
- `LLM_MAX_TOKENS=1000` — the model reasons briefly first, so a small budget
  starves the answer; 1000 leaves room for thinking + reply.

`muse-spark-1.3-contributor` remains available via `LLM_PROTOCOL=responses`
(slower first-audio, better Thai). The client keeps one keep-alive HTTP
connection across turns (no per-turn TLS handshake).

Create `.env` from `.env.example` and put your key in:

```dotenv
OPENCODE_API_KEY=your_key_here
```

You can also set `LLM_API_KEY`; that value takes precedence over `OPENCODE_API_KEY`.

The client consumes `response.output_text.delta` events from the Responses stream, so the LLM side can start flowing text before the full answer is complete.

## Layout

- `src/realtime_voice/` runtime
- `benchmark/` isolated benchmarks
- `tests/` unit tests

## Status

Experimental prototype; model-specific STT/TTS backends are kept behind adapters so the same conversation loop can later move to a GPU server.

## Install

```bash
uv venv && uv pip install -e '.[dev,audio,stt-mlx,tts-local]'
cp .env.example .env
```

## Run

```bash
uv run realtime-voice                    # microphone + speaker (local MLX STT, pause ~1s to end a turn; mic pauses while bot speaks)
uv run realtime-voice --text             # type turns on stdin, no mic needed
uv run realtime-voice --text --mute      # synthesize but skip playback
uv run realtime-voice --text --max-turns 5 < turns.txt
uv run realtime-voice --stt-only          # microphone to text only, no LLM/TTS
```

From OpenCode: `/voice-chat <opening topic>` relays between you and the loop.

Per-turn timings (first-audio, chunks, synth) go to stderr; the transcript goes to stdout.

## Languages

Thai is the default (Qwen3-ASR MLX + MMS Thai TTS). English mode:

```bash
uv pip install -e '.[stt-en,tts-en]'
brew install espeak-ng          # Kokoro phonemizer backend
uv run realtime-voice --text --lang en
```

## Live captions

`--live` shows the words as you speak (mlx-whisper streaming, Thai + English),
then sends the turn on your usual silence pause:

```bash
uv pip install -e '.[stt-live]'
uv run realtime-voice --live --preset ielts
```

Live mode re-decodes every ~2s, so it uses noticeably more CPU than the
default utterance backends. Omit `--live` for the lighter, preview-free loop.

## Session recording

`--record DIR` keeps everything past the in-memory transcript: per-turn
transcript (`transcript.md`), user mic audio (`mic.wav`), agent voice
(`agent.wav`), and settings + timings (`meta.json`) under `DIR/<timestamp>/`.
Band scores requested mid-session are computed from the full transcript,
not the compressed rolling summary.

English uses Parakeet-TDT 0.6B (MLX) for STT and Kokoro-82M for TTS with
English prompts. Precedence: `--system-prompt` > `--lang` builtin >
`LLM_SYSTEM_PROMPT` env > language default. (`VOICE_LANG` env also works
when `--lang` is omitted.)

The realtime loop is designed for streaming operation. Default TTS is local MMS Thai (`facebook/mms-tts-tha`); `--lang en` switches to Kokoro-82M + Parakeet-TDT. Live STT uses energy endpointing over the local model, measurable offline via `benchmark/asr_benchmark.py` (mlx-qwen3-asr).
