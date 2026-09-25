"""Bounded conversation history with a rolling summary.

The LLM payload stays at ``max_recent + 1`` messages no matter how long
the conversation gets, so per-turn latency stops growing with history.
Older turns are folded into ``summary`` via a caller-provided
summarizer (normally one LLM call), incrementally — each old turn is
summarized exactly once.
"""

from dataclasses import dataclass, field


@dataclass
class ConversationHistory:
    max_recent: int = 8
    summary: str = ''
    _entries: list = field(default_factory=list)
    _summarized: int = 0

    def add(self, role, content):
        self._entries.append({'role': role, 'content': content})

    def __len__(self):
        return len(self._entries)

    def build(self, summarize=None):
        """Messages to send to the LLM. ``summarize`` takes a list of
        old messages and returns a short string; called only when new
        old turns appear."""
        if len(self._entries) <= self.max_recent:
            return list(self._entries)
        cutoff = len(self._entries) - self.max_recent
        if cutoff > self._summarized and summarize is not None:
            new = summarize(self._entries[self._summarized:cutoff])
            self.summary = f'{self.summary}\n{new}'.strip() if self.summary else new
            self._summarized = cutoff
        messages = list(self._entries[cutoff:])
        if self.summary:
            messages.insert(0, {
                'role': 'system',
                'content': f'Summary of earlier conversation: {self.summary}',
            })
        return messages
