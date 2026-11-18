"""Single entry point used by the Flask app and by the experiment runner.

Owner: B (shared contract). Everything RAG-related stays behind this function so
the UI and the runner always measure the same path.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from ragbot import llm_client, logging_utils, prompt_builder, retriever
from ragbot.config import load_settings, load_system_prompt
from ragbot.types import MitigationFlags, PipelineResult


def answer(question: str, collection: str, flags: MitigationFlags) -> PipelineResult:
    """Answer `question` from `collection` and return the full trace of the run."""
    settings = load_settings()
    system_prompt = load_system_prompt()

    started = time.perf_counter()
    chunks = retriever.retrieve(question, collection, settings.retrieval_k, flags)
    messages = prompt_builder.build_messages(system_prompt, question, chunks, flags)
    response = llm_client.chat(messages, settings.chat_model, settings.temperature, settings.seed)

    result = PipelineResult(
        question=question,
        chunks=chunks,
        messages=messages,
        response=response,
        flags=flags,
        model=settings.chat_model,
        collection=collection,
        latency_s=time.perf_counter() - started,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    logging_utils.log_result(result, {})
    return result
