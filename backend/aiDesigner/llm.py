"""
Provider-agnostic LLM client with tool-calling, using plain HTTP (requests).

Provider is selected with env vars:
    LLM_PROVIDER = anthropic | openai | ollama   (default: anthropic)
    LLM_MODEL    = model name (sensible default per provider)
    ANTHROPIC_API_KEY / OPENAI_API_KEY           (not needed for ollama)
    OLLAMA_URL   = http://localhost:11434 (default)

Only one method matters: chat(messages, tool) -> {"tool_input": dict|None, "text": str}
`tool` is a dict: {"name", "description", "input_schema"} (JSON Schema).
"""

import os
import json
import time
import random
import logging

import requests

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-5",
    "openai": "gpt-4o-mini",
    "ollama": "llama3.1",
}


class RateLimited(Exception):
    """Provider returned 429 after exhausting retries — surfaced to the caller."""


def _post_with_retry(url, headers, payload, timeout, attempts=4):
    """
    POST with exponential backoff on 429/5xx. Free LLM tiers cap tokens-per-minute,
    and the schema-heavy tool definition makes bursts easy to hit; honouring
    Retry-After and backing off keeps the agent usable instead of failing hard.
    """
    delay = 2.0
    for attempt in range(1, attempts + 1):
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if resp.status_code == 429 or resp.status_code >= 500:
            if attempt == attempts:
                if resp.status_code == 429:
                    raise RateLimited(
                        "LLM provider rate limit reached. Wait about a minute and try again."
                    )
                resp.raise_for_status()
            wait = float(resp.headers.get("Retry-After") or 0) or delay
            wait += random.uniform(0, 0.5)  # jitter so parallel callers don't sync up
            logging.warning("LLM %s — retry %d/%d in %.1fs", resp.status_code, attempt, attempts, wait)
            time.sleep(min(wait, 30))
            delay *= 2
            continue
        resp.raise_for_status()
        return resp
    raise RateLimited("LLM provider rate limit reached.")


class LLMClient:
    def __init__(self, provider=None, model=None, timeout=90):
        self.provider = (provider or os.getenv("LLM_PROVIDER", "anthropic")).lower()
        if self.provider not in DEFAULT_MODELS:
            raise ValueError("unsupported LLM_PROVIDER: " + self.provider)
        self.model = model or os.getenv("LLM_MODEL") or DEFAULT_MODELS[self.provider]
        self.timeout = timeout

    # ---- public ----

    def chat(self, messages, tool):
        """messages: [{"role": "system"|"user"|"assistant", "content": str}]"""
        if self.provider == "anthropic":
            return self._anthropic(messages, tool)
        if self.provider == "openai":
            return self._openai(messages, tool)
        return self._ollama(messages, tool)

    # ---- providers ----

    def _anthropic(self, messages, tool):
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        convo = [m for m in messages if m["role"] != "system"]
        resp = _post_with_retry(
            "https://api.anthropic.com/v1/messages",
            {
                "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            {
                "model": self.model,
                "max_tokens": 4096,
                "system": system,
                "messages": convo,
                "tools": [tool],
                "tool_choice": {"type": "tool", "name": tool["name"]},
            },
            self.timeout,
        )
        body = resp.json()
        tool_input, text = None, ""
        for block in body.get("content", []):
            if block["type"] == "tool_use" and block["name"] == tool["name"]:
                tool_input = block["input"]
            elif block["type"] == "text":
                text += block["text"]
        return {"tool_input": tool_input, "text": text}

    def _openai(self, messages, tool):
        # OPENAI_BASE_URL lets any OpenAI-compatible API serve this provider:
        # Groq (https://api.groq.com/openai/v1), Google Gemini
        # (https://generativelanguage.googleapis.com/v1beta/openai), OpenRouter, etc.
        base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        resp = _post_with_retry(
            base + "/chat/completions",
            {"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]},
            {
                "model": self.model,
                "messages": messages,
                "tools": [{
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["input_schema"],
                    },
                }],
                "tool_choice": {"type": "function", "function": {"name": tool["name"]}},
            },
            self.timeout,
        )
        msg = resp.json()["choices"][0]["message"]
        tool_input = None
        if msg.get("tool_calls"):
            tool_input = json.loads(msg["tool_calls"][0]["function"]["arguments"])
        return {"tool_input": tool_input, "text": msg.get("content") or ""}

    def _ollama(self, messages, tool):
        url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        resp = _post_with_retry(
            url + "/api/chat",
            {},
            {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "tools": [{
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["input_schema"],
                    },
                }],
            },
            self.timeout,
        )
        msg = resp.json()["message"]
        tool_input = None
        calls = msg.get("tool_calls") or []
        if calls:
            tool_input = calls[0]["function"]["arguments"]
            if isinstance(tool_input, str):
                tool_input = json.loads(tool_input)
        return {"tool_input": tool_input, "text": msg.get("content") or ""}
