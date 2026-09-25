# Thai Realtime Voice

Realtime Thai voice conversation on Apple Silicon.

Pipeline: microphone -> local streaming STT -> streaming LLM API -> local Thai TTS -> speaker.

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

- `src/thai_realtime_voice/` runtime
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
uv run thai-voice                    # microphone + speaker (local MLX STT, pause ~1s to end a turn; mic pauses while bot speaks)
uv run thai-voice --text             # type turns on stdin, no mic needed
uv run thai-voice --text --mute      # synthesize but skip playback
uv run thai-voice --text --max-turns 5 < turns.txt
```

From OpenCode: `/voice-chat <opening topic>` relays between you and the loop.

Per-turn timings (first-audio, chunks, synth) go to stderr; the transcript goes to stdout.

The realtime loop is designed for streaming operation. Default TTS is local MMS Thai (`facebook/mms-tts-tha`); live STT still needs a streaming backend (`Qwen3ASRStreaming.backend`), measurable offline via `benchmark/asr_benchmark.py` (mlx-qwen3-asr).
