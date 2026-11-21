"""Single entry point used by the Flask app and by the experiment runner.

Owner: B (shared contract). Everything RAG-related stays behind this function so
the UI and the runner always measure the same path.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from ragbot import llm_client, logging_utils, prompt_builder, retriever
from ragbot.config import Settings, load_settings, load_system_prompt
from ragbot.mitigations import get_mitigation
from ragbot.types import Chunk, MitigationFlags, PipelineResult


def answer(question: str, collection: str, flags: MitigationFlags) -> PipelineResult:
    """Answer `question` from `collection` and return the full trace of the run."""
    settings = load_settings()
    system_prompt = load_system_prompt()

    started = time.perf_counter()

    if flags.input_filter:
        blocked, rule = get_mitigation("input_filter").apply(question)
        if blocked:
            # Stop before retrieval so a rejected question cannot shape the context.
            result = _make_result(
                settings=settings,
                question=question,
                collection=collection,
                flags=flags,
                chunks=[],
                messages=[],
                response=get_mitigation("input_filter").BLOCKED_RESPONSE,
                started=started,
                blocked_by="input_filter",
            )
            logging_utils.log_result(result, {"input_filter_rule": rule})
            return result

    chunks = retriever.retrieve(question, collection, settings.retrieval_k, flags)
    messages = prompt_builder.build_messages(system_prompt, question, chunks, flags)
    response = llm_client.chat(messages, settings.chat_model, settings.temperature, settings.seed)

    blocked_by = None
    extra: dict = {}
    if flags.output_filter:
        raw_response = response
        response, blocked = get_mitigation("output_filter").apply(response, system_prompt)
        if blocked:
            blocked_by = "output_filter"
            # The raw answer is evidence; the user only sees the safe replacement.
            extra["raw_response"] = raw_response

    result = _make_result(
        settings=settings,
        question=question,
        collection=collection,
        flags=flags,
        chunks=chunks,
        messages=messages,
        response=response,
        started=started,
        blocked_by=blocked_by,
    )
    logging_utils.log_result(result, extra)
    return result


def _make_result(
    *,
    settings: Settings,
    question: str,
    collection: str,
    flags: MitigationFlags,
    chunks: list[Chunk],
    messages: list[dict],
    response: str,
    started: float,
    blocked_by: str | None = None,
) -> PipelineResult:
    return PipelineResult(
        question=question,
        chunks=chunks,
        messages=messages,
        response=response,
        flags=flags,
        model=settings.chat_model,
        collection=collection,
        latency_s=time.perf_counter() - started,
        timestamp=datetime.now(timezone.utc).isoformat(),
        blocked_by=blocked_by,
    )
