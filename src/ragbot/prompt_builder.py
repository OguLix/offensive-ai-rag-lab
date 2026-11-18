"""Builds the message list sent to the LLM.

Owner: B. This is the seam where document text must be marked as untrusted data,
so an instruction inside a document cannot read as a system rule.
"""

from __future__ import annotations

from ragbot.mitigations import get_mitigation
from ragbot.types import Chunk, MitigationFlags


def build_messages(
    system_prompt: str,
    question: str,
    chunks: list[Chunk],
    flags: MitigationFlags,
) -> list[dict]:
    """Return the final prompt sent to the model, keeping instructions and data apart."""
    if flags.prompt_hardening:
        system_prompt = get_mitigation("prompt_hardening").apply(system_prompt)

    if flags.context_isolation:
        context = get_mitigation("context_isolation").apply(chunks)
        user_content = f"{context}\n\nPERTANYAAN PENGGUNA:\n{question}"
    else:
        # Baseline: raw passages without extra framing, so an attack result
        # reflects the document text rather than a hidden wrapper.
        context = "\n\n".join(chunk.text for chunk in chunks)
        user_content = f"{context}\n\n{question}" if context else question

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
