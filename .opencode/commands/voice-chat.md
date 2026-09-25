---
description: Talk through the realtime voice loop (optional: language and topic)
---

Chat with the user through this project's realtime voice loop. First check the setup:

!`test -f .env && echo "env: ok" || echo "env: MISSING - copy .env.example to .env and set OPENCODE_API_KEY"`

Then start the loop in text mode (no microphone needed) with the requested language and opening topic, send each user message to the loop's stdin, and show the bot's spoken replies:

uv run realtime-voice --text --lang <language>

Start the loop in the harness's background mode by default; do not run the loop shell in the foreground. Because the harness's background shell cannot accept later stdin writes directly, use a temporary FIFO: create the input FIFO and keep a writer open with `tail -f /dev/null`, then run the loop with the FIFO as stdin and separate stdout/stderr files. After each user message, append it to the FIFO and wait for that turn's timing line on stderr before showing the agent's stdout reply. Do not use `sleep infinity`; it is unsupported by macOS `sleep`. Send `stop\n` and terminate the loop plus its FIFO writer when the user says stop.

Interpret the command arguments as:
- `<language> [opening topic]`, where language is a BCP 47 language code such as `en` or `es`.
- `[opening topic]`, meaning English (`en`) and the entire argument string as the opening topic.
- No arguments, meaning English (`en`) and no opening topic.

The user's raw arguments are: $ARGUMENTS

Use a sensible BCP 47 code for a named language and do not ask the user to confirm it. If the first argument is a language code, use it as the language and the remaining text as the opening topic. Otherwise, use English and treat all arguments as the opening topic.

Keep relaying until the user says stop. Never print API keys. The loop prints per-turn timings (first-audio, chunks, synth) on stderr.
