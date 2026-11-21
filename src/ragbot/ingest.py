"""Splits corpus files into chunks and loads them into a vector collection.

Owner: A. Supports both programmatic calls (`ingest_directory`) and CLI usage
(`python -m ragbot.ingest --collection kb_clean --path data/corpus`).
"""

from __future__ import annotations

import argparse
import logging
import re
from collections.abc import Sequence
from pathlib import Path

from ragbot import vectorstore
from ragbot.config import PROJECT_ROOT
from ragbot.mitigations import get_mitigation
from ragbot.types import MitigationFlags

LOGGER = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = frozenset({".md", ".txt"})
IGNORED_FILENAMES = frozenset({"readme.md"})
LAB_ATTACK_HEADER = "# SERANGAN S2/S3: hanya untuk lab proyek"
DEFAULT_MAX_CHUNK_CHARS = 800

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")


def ingest_directory(
    path: str | Path,
    collection: str,
    flags: MitigationFlags | None = None,
    *,
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
) -> int:
    """Ingest every supported file under `path` and return the number of chunks stored.

    `flags` matters here because `ingest_sanitizer` and `provenance_check` act
    before text ever reaches the vector store.
    """
    active_flags = flags or MitigationFlags()
    directory = Path(path)
    if not directory.is_dir():
        raise FileNotFoundError(f"ingest path is not an existing directory: {directory}")

    if collection == "kb_clean" and _is_poisoned_path(directory):
        raise ValueError("refusing to ingest data/poisoned into kb_clean")

    store = vectorstore.get_collection(collection)
    provenance = get_mitigation("provenance_check") if active_flags.provenance_check else None
    sanitizer = get_mitigation("ingest_sanitizer") if active_flags.ingest_sanitizer else None

    ids: list[str] = []
    texts: list[str] = []
    metadatas: list[dict[str, object]] = []

    for file_path in _iter_documents(directory):
        source = _source_label(file_path)
        raw_text = file_path.read_text(encoding="utf-8")
        text, is_attack_doc = _strip_lab_header(raw_text)

        if collection == "kb_clean" and is_attack_doc:
            raise ValueError(f"refusing to ingest lab attack document {source!r} into kb_clean")

        if provenance is not None and not provenance.apply(source, text):
            LOGGER.info("skipped %s: rejected by provenance_check", source)
            continue

        if sanitizer is not None:
            text = sanitizer.apply(text)

        chunks = chunk_text(text, max_chars=max_chunk_chars)
        if not chunks:
            continue

        doc_id = file_path.stem
        for index, chunk in enumerate(chunks):
            ids.append(f"{source}::chunk-{index}")
            texts.append(chunk)
            metadatas.append(
                {
                    "doc_id": doc_id,
                    "source": source,
                    "chunk_index": index,
                    "lab_attack_doc": is_attack_doc,
                }
            )

    stored = vectorstore.add_chunks(store, ids, texts, metadatas)
    LOGGER.info("ingested %d chunks from %s into %s", stored, directory, collection)
    return stored


def chunk_text(text: str, max_chars: int = DEFAULT_MAX_CHUNK_CHARS) -> list[str]:
    """Split `text` into paragraph-aligned chunks no longer than `max_chars`."""
    if max_chars <= 0:
        raise ValueError("max_chars must be a positive integer")

    paragraphs = [part.strip() for part in _PARAGRAPH_SPLIT.split(text.strip()) if part.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        pieces = _split_long_paragraph(paragraph, max_chars)
        for piece in pieces:
            candidate = f"{current}\n\n{piece}" if current else piece
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = piece
    if current:
        chunks.append(current)
    return chunks


def _split_long_paragraph(paragraph: str, max_chars: int) -> list[str]:
    if len(paragraph) <= max_chars:
        return [paragraph]

    words = paragraph.split()
    pieces: list[str] = []
    current = ""
    for word in words:
        if len(word) > max_chars:
            if current:
                pieces.append(current)
                current = ""
            for start in range(0, len(word), max_chars):
                pieces.append(word[start : start + max_chars])
            continue
        candidate = f"{current} {word}" if current else word
        if len(candidate) <= max_chars:
            current = candidate
        else:
            pieces.append(current)
            current = word
    if current:
        pieces.append(current)
    return pieces


def _iter_documents(directory: Path) -> list[Path]:
    files: list[Path] = []
    for file_path in sorted(directory.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.name.startswith("."):
            continue
        if file_path.name.lower() in IGNORED_FILENAMES:
            continue
        if file_path.suffix.lower() in SUPPORTED_SUFFIXES:
            files.append(file_path)
    return files


def _strip_lab_header(text: str) -> tuple[str, bool]:
    # Poisoned files carry a mandatory lab-only header line (AGENTS.md Bagian 7).
    # Stripping it before embedding keeps similarity scores realistic while
    # preserving `lab_attack_doc=True` in metadata for inspection.
    normalized = text.replace("\r\n", "\n").lstrip("\ufeff")
    first_line, _, rest = normalized.partition("\n")
    if first_line.strip() == LAB_ATTACK_HEADER:
        return rest.lstrip("\n"), True
    return normalized, False


def _source_label(file_path: Path) -> str:
    resolved = file_path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _is_poisoned_path(directory: Path) -> bool:
    poisoned_root = (PROJECT_ROOT / "data" / "poisoned").resolve()
    resolved = directory.resolve()
    return resolved == poisoned_root or poisoned_root in resolved.parents


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser for `python -m ragbot.ingest`."""
    parser = argparse.ArgumentParser(
        prog="python -m ragbot.ingest",
        description="Ingest corpus or poisoned documents into a local ChromaDB collection.",
    )
    parser.add_argument(
        "--collection",
        required=True,
        help="Target collection name (must be listed in config/settings.yaml allowed_collections).",
    )
    parser.add_argument(
        "--path",
        dest="paths",
        action="append",
        required=True,
        help="Directory to ingest; repeat --path to combine directories (e.g. corpus + poisoned).",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop the target collection before ingesting.",
    )
    parser.add_argument(
        "--ingest-sanitizer",
        action="store_true",
        help="Enable M3 ingest_sanitizer while ingesting.",
    )
    parser.add_argument(
        "--provenance-check",
        action="store_true",
        help="Enable M3 provenance_check while ingesting.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: python -m ragbot.ingest --collection kb_clean --path data/corpus."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = build_parser().parse_args(argv)

    if args.reset:
        vectorstore.delete_collection(args.collection)

    flags = MitigationFlags(
        ingest_sanitizer=args.ingest_sanitizer,
        provenance_check=args.provenance_check,
    )
    total = 0
    for raw_path in args.paths:
        total += ingest_directory(raw_path, args.collection, flags)

    LOGGER.info("done: %d total chunks in %s", total, args.collection)
    return total


if __name__ == "__main__":
    main()
