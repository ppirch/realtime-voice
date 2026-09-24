# Thai Realtime Voice

Realtime Thai voice conversation on Apple Silicon.

Pipeline: microphone -> local streaming STT -> streaming LLM API -> local Thai TTS -> speaker.

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

Configure `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` in `.env`.

## Run

```bash
python -m thai_realtime_voice
```

The realtime loop is designed for streaming/interruptible operation. The concrete Qwen3-ASR MLX and FastThaiG2P/Kokoro adapters are intentionally isolated from the benchmark suite.
