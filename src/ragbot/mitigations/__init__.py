"""Mitigation registry: maps a MitigationFlags field to the module implementing it.

The pipeline asks this registry what is enabled instead of importing every
mitigation, so a disabled mitigation costs nothing and cannot run by accident.
"""

from __future__ import annotations

import importlib
from types import ModuleType

from ragbot.types import MitigationFlags

MITIGATION_MODULES: dict[str, str] = {
    "prompt_hardening": "ragbot.mitigations.prompt_hardening",
    "input_filter": "ragbot.mitigations.input_filter",
    "output_filter": "ragbot.mitigations.output_filter",
    "context_isolation": "ragbot.mitigations.context_isolation",
    "retrieval_sanitizer": "ragbot.mitigations.retrieval_sanitizer",
    "ingest_sanitizer": "ragbot.mitigations.ingest_sanitizer",
    "provenance_check": "ragbot.mitigations.provenance",
}


def enabled_flags(flags: MitigationFlags) -> list[str]:
    """Return names of the mitigations switched on for this request, in registry order."""
    return [name for name in MITIGATION_MODULES if getattr(flags, name)]


def get_mitigation(name: str) -> ModuleType:
    """Import a mitigation module lazily; an unknown name is a programming error."""
    module_path = MITIGATION_MODULES.get(name)
    if module_path is None:
        raise ValueError(f"unknown mitigation: {name}")
    return importlib.import_module(module_path)
