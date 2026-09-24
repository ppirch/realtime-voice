# E2E voice benchmark results (2026-09-25)

Latest code path: muse-spark-1.3-contributor via Go `/responses` (streaming)
→ Thai chunker (target 30 / max 60 chars) → live MMS-TTS Thai synth (MPS)
→ 24 kHz mono WAV. Simulated user turns via macOS Kanya voice.
LLM streaming waits are preserved as silence in the audio — nothing cut.

WAV/MP3/timelines live under `benchmark/results/` (gitignored, local only):
`e2e_mms_01_food`, `e2e_mms_02_bangkok`, `e2e_mms_03_daily`, `e2e_mms_04_work`.

## Per-turn first-audio (seconds, = wait for LLM chunk 1)

| Example | Turns | First-audio per turn | Avg |
|---|---|---|---|
| 01 food (5 turns) | 5 | 5.6, 18.6, 9.8, 7.5, 19.2 | 12.1 |
| 02 bangkok (4 turns) | 4 | 13.3, 16.0, 18.4, 9.6 | 14.3 |
| 03 daily (3 turns) | 3 | 8.8, 10.3, 5.6 | 8.2 |
| 04 work (4 turns) | 4 | 7.8, 12.5, 18.6, 6.5 | 11.3 |
| **Overall** | **16** | min 5.6 / max 19.2 | **11.8** |

## Pipeline stats

- Chunks/turn: 4.8–10.7 avg (29/34/32/19 chunks) — chunker splits aggressively once ~30 chars accumulate; inter-chunk gaps ≈ 0.0–0.1s (streaming flows, then TTS-bound).
- MMS synth/chunk (live, MPS): avg ~0.30s (282–314ms per example).
- MMS model load (cold, cached weights): 4.1s.
- Unspeakable chunks degraded to silence by guard: 4× (all `'3.'` list markers — VITS overflows on digit/punctuation-only input).
- STT (offline reference, mlx-qwen3-asr 0.6B): 0.37–0.41s / RTF ~0.13, Thai exact-match 2/3 clips.

## vs previous run (old chunker, 40-word capped prompt)

Old: 1 chunk/turn, first-audio ≈ full response (~9.6/6.6/9.7s avg).
New: multi-chunk streaming works (sub-0.1s inter-chunk gaps), but first-audio is
still 5.6–19.2s because (a) the env prompt is uncapped → longer replies before
~30 chars accumulate, and (b) endpoint latency varied more this run.

## Bottleneck (unchanged)

LLM time-to-first-chunk dominates everything (11.8s avg vs 0.3s TTS vs 0.4s STT).
Next levers: cap reply length via system prompt, shrink first-flush threshold,
and/or try `/chat/completions` models for faster first tokens.

## Run 2 — realtime system prompt (same 4 examples, 16 turns)

Prompt now forces: spoken Thai only, 1–2 short sentences, no lists/markdown/
emoji/URLs/symbols, numbers as Thai words, one idea + follow-up per turn.

| Example | First-audio per turn (s) | Avg | Chunks/turn |
|---|---|---|---|
| 01 food (5) | 11.4, 10.6, 9.3, 15.9, 23.3 | 14.1 | 2.0 |
| 02 bangkok (4) | 10.6, 8.4, 8.6, 8.4 | 9.0 | 1.8 |
| 03 daily (3) | 11.5, 8.3, 5.7 | 8.5 | 1.7 |
| 04 work (4) | 11.1, 9.9, 15.6, 10.0 | 11.6 | 1.8 |
| **Overall** | min 5.7 / max 23.3 | **11.2** | **1.8** |

What improved: replies are short and conversational
(e.g. `สวัสดีครับคุณต้น / วันนี้อยากคุยอะไรดีครับ`), files 30–55% shorter,
**zero** unspeakable-chunk guard hits (was 4× `'3.'`).
What did not: first-audio barely moved (11.8s → 11.2s) — shortening replies
does not reduce time-to-first-chunk, so that wait is server-side, not
reply-length-bound. Prompt fix buys speakability + shorter turns, not latency.
