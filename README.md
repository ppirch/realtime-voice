# Thai Realtime Voice

Realtime Thai voice conversation on Apple Silicon.

Pipeline: microphone -> local streaming STT -> streaming LLM API -> local Thai TTS -> speaker.

## LLM: OpenCode Zen / Muse Spark 1.3 Contributor

The default configuration is:

- model: `muse-spark-1.3-contributor`
- endpoint: `https://opencode.ai/zen/go/v1/responses`
- protocol: OpenAI Responses API
- SDK compatibility: `@ai-sdk/openai`

OpenCode lists Muse Spark 1.3 Contributor on the Go endpoint as a Responses API model with `@ai-sdk/openai`. citeturn611406view0turn135984search1

Create `.env` from `.env.example` and put your key in:

```dotenv
OPENCODE_API_KEY=your_key_here
```

You can also set `LLM_API_KEY`; that value takes precedence over `OPENCODE_API_KEY`.

The client consumes `response.output_text.delta` events from the Responses stream, so the LLM side can start flowing text before the full answer is complete. citeturn629523search0

## Layout

- `src/thai_realtime_voice/` runtime
- `benchmark/` isolated benchmarks
- `tests/` unit tests

## Status

Experimental prototype; model-specific STT/TTS backends are kept behind adapters so the same conversation loop can later move to a GPU server.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,audio]'
cp .env.example .env
```

## Run

```bash
python -m thai_realtime_voice
```

The realtime loop is designed for streaming/interruptible operation. The concrete Qwen3-ASR MLX and FastThaiG2P/Kokoro adapters are intentionally isolated from the benchmark suite.
