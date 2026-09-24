---
description: Talk through the realtime Thai voice loop in the terminal
---

Chat with the user through this project's realtime Thai voice loop. First check the setup:

!`test -f .env && echo "env: ok" || echo "env: MISSING - copy .env.example to .env and set OPENCODE_API_KEY"`

Then start the loop in text mode (no microphone needed) with the opening topic below, send each user message to the loop's stdin, and show the bot's spoken replies:

uv run thai-voice --text

Opening topic: $ARGUMENTS

Keep relaying until the user says stop. Never print API keys. The loop prints per-turn timings (first-audio, chunks, synth) on stderr.
