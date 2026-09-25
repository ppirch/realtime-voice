---
description: Talk through the realtime voice loop (optional: language and topic)
---

Chat with the user through this project's realtime voice loop: the user types text, the loop answers with speech. First check the setup:

!`test -f .env && echo "env: ok" || echo "env: MISSING - copy .env.example to .env and set OPENCODE_API_KEY"`

Then kill any stale loops from earlier sessions (they fight over the speaker and hold memory):

!`pkill -f 'realtime-voice --text' 2>/dev/null || true`

Then start the loop in text mode (user types, no microphone needed) with spoken replies through the speaker, using the requested language and opening topic. Send each user message to the loop's stdin, let the bot's spoken replies play aloud, and show the reply text:

uv run realtime-voice --text --lang <language> --system-prompt "<concise prompt below>"

Rules:
- Always pass `--text` (typed turns). Never pass `--mute`: replies must play through the speaker.
- Always pass `--system-prompt` with the matching concise prompt below, so every reply stays 1-2 short speakable sentences like a real conversation (keep in sync with `TH_SYSTEM_PROMPT` / `EN_SYSTEM_PROMPT` in `src/realtime_voice/config.py`):
  - English: `You are a realtime English voice assistant. Reply in spoken English only: 1-2 short sentences per turn, under 60 characters when possible. Never use lists, markdown, emoji, URLs, or symbols. One idea per turn, then ask a brief follow-up to keep talking.`
  - Thai: `You are a realtime Thai voice assistant. Reply in spoken Thai only: 1-2 short sentences per turn, under 60 characters when possible. Never use lists, markdown, emoji, URLs, or symbols. Write numbers as Thai words. One idea per turn, then ask a brief follow-up to keep talking.`

Assistant speech: everything you say to the user must be heard, not just read. Keep a warm TTS daemon running so the model loads once per session instead of once per message:

uv run realtime-voice-say --listen --lang <language>

Give it its own FIFO + `tail -f /dev/null` writer, like the voice loop (separate files). Append every assistant message (questions, prompts, status) to the say FIFO as well as showing the text. Do NOT pipe the loop's own Agent replies through it — the loop already speaks those through its speaker; double-piping echoes. Terminate the say daemon together with the loop when the user says stop.

Start the loop in the harness's background mode by default; do not run the loop shell in the foreground. Because the harness's background shell cannot accept later stdin writes directly, use a temporary FIFO: create the input FIFO and keep a writer open with `tail -f /dev/null`, then run the loop with the FIFO as stdin and separate stdout/stderr files. After each user message, append it to the FIFO and wait for that turn's timing line on stderr before showing the agent's stdout reply. Do not use `sleep infinity`; it is unsupported by macOS `sleep`. Send `stop\n` and terminate the loop plus its FIFO writer when the user says stop.

Interpret the command arguments as:
- `<language> [opening topic]`, where language is a BCP 47 language code such as `en` or `es`.
- `[opening topic]`, meaning English (`en`) and the entire argument string as the opening topic.
- No arguments, meaning English (`en`) and no opening topic.

The user's raw arguments are: $ARGUMENTS

Use a sensible BCP 47 code for a named language and do not ask the user to confirm it. If the first argument is a language code, use it as the language and the remaining text as the opening topic. Otherwise, use English and treat all arguments as the opening topic.

Keep relaying until the user says stop. Never print API keys. The loop prints per-turn timings (first-audio, chunks, synth) on stderr.
