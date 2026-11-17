"""Thin wrapper around the local Ollama client.

Owner: C. Phase 0 stub only. Keeping the client here means the model name and
generation parameters always come from config, never from a call site.
"""

from __future__ import annotations


def chat(messages: list[dict], model: str, temperature: float, seed: int) -> str:
    """Send `messages` to the local model and return the assistant text."""
    raise NotImplementedError("chat is implemented by owner C in Phase 1")
