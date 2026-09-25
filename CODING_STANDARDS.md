# Coding Standards

Enforced by `ruff check` (no separate config; default rules). The rest is convention.

## Layout

- Runtime: `src/realtime_voice/`. One adapter per STT/TTS backend (`stt_mlx.py`, `stt_parakeet.py`, `stt_live.py`, `tts_mms.py`, `tts_kokoro.py`).
- Shared contracts live in one place: `stt_endpoint.py` (`MODEL_SR`, `Utterance`, `Endpointer`, `resample`, `utterance_stream`). Never import shared types from a sibling adapter.
- Orchestration (`app.py`) picks adapters; it must not contain transcription, synthesis, or endpoint math.

## Adapters

- Same constructor shape: tuning params (`silence_rms`, `silence_ms`, `min_speech_ms`, `max_utterance_s`) plus `stream(audio_chunks, sample_rate=16000)` yielding `Utterance` events (`is_final=False` = live preview, `True` = turn).
- Heavy dependencies (model weights, `mlx-*`, `torch`) import lazily inside `__init__`, never at module top. `--help` and `--text` must work without optional extras installed.
- Constructors that load weights take an injectable seam (`transcriber=`) so endpoint logic is unit-testable without downloads. Tests use stub transcribers and fake mics, never mocks of internal methods.
- No pass-through modules: if the interface matches the implementation, delete it and call the target directly.

## Style

- Short functions, plain data flow, no speculative generality (no flags, hooks, or factories until a second caller exists).
- Errors: raise `RuntimeError`/`SystemExit` with a message telling the user what to install or set.
- Console: human status lines go to stderr; only transcripts and results go to stdout.
- Commit messages: Conventional Commits, short and scopeless (`feat:`, `fix:`, `refactor:`, `chore:`, `docs:`).
