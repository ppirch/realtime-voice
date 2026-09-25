# Contributing

## Setup

Requirements: macOS on Apple Silicon, `uv`, an OpenCode Zen API key.

```bash
uv venv && uv pip install -e '.[dev,audio,stt-mlx,tts-local]'
cp .env.example .env   # then set OPENCODE_API_KEY
```

Optional extras per feature:

```bash
uv pip install -e '.[stt-en,tts-en]'  # English voice (Parakeet + Kokoro) +: brew install espeak-ng
uv pip install -e '.[stt-live]'       # live word previews (mlx-whisper)
```

## Run

```bash
uv run realtime-voice                    # mic + speaker (default Thai)
uv run realtime-voice --text             # type turns instead of mic
uv run realtime-voice --preset ielts     # IELTS examiner mock (English)
uv run realtime-voice --stt-only         # mic to text, no LLM/TTS
```

## Change flow

1. Keep changes small and scoped; one work unit per commit.
2. Add or update tests alongside the change (`tests/test_*.py`, run with `uv run pytest -q`).
3. Lint the files you touched: `uv run ruff check src tests`.
4. Smoke-test behavior when the change touches the voice path (text mode or a real mic run).
5. Commit with a Conventional Commit message (`feat:`, `fix:`, `refactor:`, `chore:`, `docs:` — short, no scope) and push to `origin/main`.

## Don't commit

`.env`, anything under `benchmark/results/`, model weights, or local-only paths.
Follow the adapter and seam conventions in CODING_STANDARDS.md.
