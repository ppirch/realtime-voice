"""Bounded conversation history with a rolling summary.

The LLM payload stays near ``max_recent + 1`` messages no matter how long
the conversation gets, so per-turn latency stops growing with history.
Older turns are folded into ``summary`` via a caller-provided
summarizer (normally one LLM call), incrementally — each old turn is
summarized exactly once.

Summarization runs in a background daemon thread: ``build()`` never blocks
on it. While a summary is in flight, the not-yet-summarized turns stay in
the payload (nothing is dropped); the next ``build()`` after completion
folds the result in and trims back down.
"""

import sys
import threading
from dataclasses import dataclass, field


@dataclass
class ConversationHistory:
    max_recent: int = 8
    summary: str = ''
    _entries: list = field(default_factory=list)
    _summarized: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _pending: threading.Thread | None = None
    _pending_end: int = 0
    _pending_result: str | None = None

    def add(self, role, content):
        self._entries.append({'role': role, 'content': content})

    def __len__(self):
        return len(self._entries)

    def transcript(self):
        """Every turn, uncompressed. Used for full-fidelity final scoring;
        the per-turn loop stays bounded via build()."""
        return list(self._entries)

    def wait(self):
        """Block until any in-flight summary lands (tests, session end)."""
        pending = self._pending
        if pending is not None:
            pending.join()

    def _reap(self):
        """Fold a finished background summary in (non-blocking)."""
        with self._lock:
            pending, result, end = self._pending, self._pending_result, self._pending_end
        if pending is None or pending.is_alive():
            return
        pending.join()
        with self._lock:
            self._pending, self._pending_result = None, None
        if result is not None:
            self.summary = f'{self.summary}\n{result}'.strip() if self.summary else result
            self._summarized = end

    def _launch(self, summarize, start, end):
        snapshot = list(self._entries[start:end])

        def run():
            try:
                result = summarize(snapshot)
            except Exception as e:  # noqa: BLE001 -- background thread must survive any summarizer failure
                print(f"background summary failed ({e}); retrying next turn",
                      file=sys.stderr, flush=True)
                result = None
            with self._lock:
                self._pending_result = result
                # on failure keep _pending cleared but _summarized stays:
                # the range retries on a later turn
                if result is None:
                    self._pending = None

        with self._lock:
            self._pending = threading.Thread(target=run, daemon=True)
            self._pending_end = end
            self._pending.start()

    def build(self, summarize=None):
        """Messages to send to the LLM. ``summarize`` takes a list of
        old messages and returns a short string; it runs in the
        background and is called only when new old turns appear."""
        self._reap()
        if len(self._entries) <= self.max_recent:
            return list(self._entries)
        cutoff = len(self._entries) - self.max_recent
        if cutoff > self._summarized and summarize is not None:
            with self._lock:
                in_flight = self._pending is not None
            if not in_flight:
                self._launch(summarize, self._summarized, cutoff)
        # Payload covers back to the last *confirmed* summary; turns a
        # background job hasn't finished stay visible meanwhile.
        messages = list(self._entries[self._summarized:])
        if self.summary:
            messages.insert(0, {
                'role': 'system',
                'content': f'Summary of earlier conversation: {self.summary}',
            })
        return messages
