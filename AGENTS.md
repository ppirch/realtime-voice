# AGENTS.md

Agent working conventions for this repo. Humans: see CONTRIBUTING.md.
Code style: see CODING_STANDARDS.md.

## Commands

```bash
uv run pytest -q                          # full suite (must stay green)
uv run pytest tests/test_x.py -q          # one file, run often while editing
uv run ruff check src tests               # lint files you touched
printf 'hi\n' | uv run realtime-voice --text --mute --max-turns 1 --lang en  # live smoke test
```

## Commit rules

- Conventional Commits, short and scopeless: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`.
- Commit and push to `origin/main` after each work unit.
- Never commit `.env`, `benchmark/results/` (gitignored), or model weights.

## Before implementing

- State assumptions. If multiple interpretations exist, present them, don't pick silently.
- Prefer editing existing files over creating new ones. Touch only what the request needs.
- No speculative features, config flags, or abstractions for single-use code.

## Verification

- New seams get tests with stubbed dependencies (see `transcriber=` in `stt_live.py`, fakes in `test_loop.py`).
- Model weights and mic hardware are unmeasurable in CI: verify those paths with live runs
  (`--text` mode or offline WAVs through `backend.stream`), not unit tests.
- Keep the suite green: `uv run pytest -q` before every commit.

## Gotchas

- `load_dotenv()` reads the repo `.env`, so `env -u` cannot unset file vars.
- Endpoint TTFT dominates latency (5–23s); TTS ~0.3–0.6s, STT ~0.2–0.4s warm.
- `.venv` scripts hardcode the project path: after moving the directory, recreate it
  (`rm -rf .venv && uv venv && uv pip install -e '.[dev,audio,stt-mlx,tts-local]'`).
