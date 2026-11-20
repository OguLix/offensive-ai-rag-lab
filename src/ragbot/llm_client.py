"""Thin wrapper around the local Ollama client.

Owner: C. Keeping the client here means the model name and generation
parameters always come from config, never from a call site.
"""

from __future__ import annotations

import os

import ollama

# Ollama's loopback default; .env.example exposes OLLAMA_HOST for overrides.
DEFAULT_HOST = "http://127.0.0.1:11434"


def chat(messages: list[dict], model: str, temperature: float, seed: int) -> str:
    """Send `messages` to the local model and return the assistant text."""
    client = ollama.Client(host=os.getenv("OLLAMA_HOST") or DEFAULT_HOST)
    response = client.chat(
        model=model,
        messages=messages,
        options={"temperature": temperature, "seed": seed},
    )
    # ollama returns None for an empty completion; callers expect a string.
    return response.message.content or ""
