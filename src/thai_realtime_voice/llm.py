import json
import uuid

import httpx

_client = None


def _shared_client():
    """One keep-alive client: no TLS/DNS handshake on every turn."""
    global _client
    if _client is None:
        _client = httpx.Client(
            timeout=httpx.Timeout(connect=10, read=None, write=10, pool=10)
        )
    return _client


class StreamingLLM:
    """Streaming LLM client for OpenAI Chat Completions and Responses APIs."""

    def __init__(self, base_url, api_key, model, system_prompt, protocol="responses", session_id=None, max_tokens=None, reasoning_effort=None):
        self.protocol = protocol
        self.url = base_url.rstrip("/")
        if protocol == "chat_completions":
            self.url += "/chat/completions"
        elif protocol == "responses":
            self.url += "/responses"
        else:
            raise ValueError("LLM_PROTOCOL must be 'responses' or 'chat_completions'")
        self.api_key, self.model, self.system_prompt = api_key, model, system_prompt
        self.session_id = session_id or str(uuid.uuid4())
        self.max_tokens = max_tokens
        self.reasoning_effort = reasoning_effort

    def stream(self, messages):
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "thai-realtime-voice/0.1.0",
            "x-opencode-session": self.session_id,
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        if self.protocol == "responses":
            payload = {
                "model": self.model,
                "stream": True,
                "input": [
                    {"role": "system", "content": self.system_prompt},
                    *messages,
                ],
            }
            if self.max_tokens:
                payload["max_output_tokens"] = self.max_tokens
            if self.reasoning_effort:
                payload["reasoning"] = {"effort": self.reasoning_effort}
        else:
            payload = {
                "model": self.model,
                "stream": True,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    *messages,
                ],
            }
            if self.max_tokens:
                payload["max_tokens"] = self.max_tokens
            if self.reasoning_effort:
                payload["reasoning_effort"] = self.reasoning_effort

        with _shared_client().stream(
            "POST",
            self.url,
            headers=headers,
            json=payload,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line or not line.startswith("data: "):
                    continue
                raw = line[6:]
                if raw == "[DONE]":
                    continue

                data = json.loads(raw)

                if self.protocol == "responses":
                    if data.get("type") == "response.output_text.delta":
                        delta = data.get("delta")
                        if delta:
                            yield delta
                else:
                    choices = data.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {}).get("content")
                    if delta:
                        yield delta
