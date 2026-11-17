"""Shared dataclasses frozen in AGENTS.md Bagian 6.

Three modules exchange data only through these types, so changing a field here
breaks the contract and needs agreement from all three owners.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Chunk:
    """A retrieved passage plus the metadata needed to inspect it during a demo."""

    doc_id: str
    text: str
    score: float
    source: str
    meta: dict = field(default_factory=dict)


@dataclass
class MitigationFlags:
    """Per-request toggles; a disabled flag keeps a mitigation module out of the path."""

    prompt_hardening: bool = False
    input_filter: bool = False
    output_filter: bool = False
    context_isolation: bool = False
    retrieval_sanitizer: bool = False
    ingest_sanitizer: bool = False
    provenance_check: bool = False


@dataclass
class PipelineResult:
    """Everything one answer produced, so logs and evidence never need a second run."""

    question: str
    chunks: list[Chunk]
    messages: list[dict]
    response: str
    flags: MitigationFlags
    model: str
    collection: str
    latency_s: float
    timestamp: str  # ISO 8601
    blocked_by: str | None = None


def mitigation_flag_names() -> tuple[str, ...]:
    """Derive flag names from the dataclass so a new flag cannot be silently accepted.

    The Flask routes whitelist request flags with this, which keeps validation and
    the contract from drifting apart.
    """
    return tuple(MitigationFlags.__dataclass_fields__)
