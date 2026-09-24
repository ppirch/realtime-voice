# Thai Realtime Voice

Realtime Thai voice conversation on Apple Silicon.

Pipeline: microphone -> local streaming STT -> streaming LLM API -> local Thai TTS -> speaker.

## LLM: OpenCode Zen / Muse Spark 1.3 Contributor

The default configuration is:

- model: `muse-spark-1.3-contributor`
- endpoint: `https://opencode.ai/zen/go/v1/responses`
- protocol: OpenAI Responses API
- SDK compatibility: `@ai-sdk/openai`

OpenCode lists Muse Spark 1.3 Contributor on the Go endpoint as a Responses API model with `@ai-sdk/openai`.

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
uv run thai-voice                    # microphone + speaker
uv run thai-voice --text             # type turns on stdin, no mic needed
uv run thai-voice --text --mute      # synthesize but skip playback
uv run thai-voice --text --max-turns 5 < turns.txt
```

From OpenCode: `/voice-chat <opening topic>` relays between you and the loop.

Per-turn timings (first-audio, chunks, synth) go to stderr; the transcript goes to stdout.

The realtime loop is designed for streaming operation. Default TTS is local MMS Thai (`facebook/mms-tts-tha`); live STT still needs a streaming backend (`Qwen3ASRStreaming.backend`), measurable offline via `benchmark/asr_benchmark.py` (mlx-qwen3-asr).
