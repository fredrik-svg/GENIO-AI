"""Utility Retrieval-Augmented Generation helper.

This module provides a lightweight Retriever class used by the web
application.  The original repository referenced a ``rag`` module but the
file was missing which resulted in ``ModuleNotFoundError`` when importing
``Retriever`` inside ``webapp.py``.  The implementation below keeps the
requirements minimal while offering a practical document ingestion and
query flow:

* Text files from a directory tree can be ingested and chunked into
  manageable passages.
* All ingested passages are stored in a JSON index so the web
  application can answer queries without re-reading the source files on
  every request.
* Queries perform a simple keyword-overlap scoring to return the most
  relevant passages.  While intentionally lightweight, it offers
  deterministic behaviour and no external service dependencies which is
  suitable for development environments or constrained hardware like the
  Raspberry Pi mentioned in the README.

Usage from the command line mirrors the instructions in the README::

    python rag.py --ingest docs/

The resulting ``rag_store.json`` file is picked up automatically the next
 time ``Retriever`` is initialised.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - yaml is an optional dependency here
    yaml = None

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Default location where the ingested passages are stored.  The path can
# be overridden via the configuration file (``rag.store_path``).
DEFAULT_STORE_PATH = "rag_store.json"

# Text files we attempt to parse during ingestion.  Binary formats are
# intentionally ignored to keep the implementation simple and robust.
TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".rst", ".html", ".htm"}


@dataclass
class Passage:
    """Container describing an individual passage in the index."""

    text: str
    source: str
    tokens: Sequence[str]

    def to_dict(self) -> Dict[str, object]:
        return {"text": self.text, "source": self.source, "tokens": list(self.tokens)}

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "Passage":
        return cls(text=str(data["text"]), source=str(data["source"]), tokens=list(data["tokens"]))


class Retriever:
    """Simple keyword-based retriever used by the FastAPI web UI.

    Parameters
    ----------
    cfg:
        Optional configuration dictionary.  The following keys are
        recognised inside ``cfg["rag"]``:

        ``store_path`` (str):
            Location of the JSON store file.  Defaults to
            :data:`DEFAULT_STORE_PATH`.
        ``docs_path`` (str):
            Directory that should be automatically ingested when the
            store is empty.
        ``chunk_size`` (int):
            Approximate number of characters per passage when ingesting
            documents.  Defaults to 500.
        ``chunk_overlap`` (int):
            Overlap in characters between subsequent chunks.  Defaults
            to 100.
    store_path:
        Explicit override of the store file path.
    """

    def __init__(self, cfg: Optional[Dict[str, object]] = None, store_path: Optional[str] = None):
        self.cfg = cfg or {}
        rag_cfg = self.cfg.get("rag", {}) if isinstance(self.cfg.get("rag"), dict) else {}
        self.store_path = store_path or str(rag_cfg.get("store_path", DEFAULT_STORE_PATH))
        self.chunk_size = int(rag_cfg.get("chunk_size", 500))
        self.chunk_overlap = int(rag_cfg.get("chunk_overlap", 100))
        self._passages: List[Passage] = []
        self._load_store()

        # If the store is empty but a docs_path was configured, attempt a
        # lazy ingestion so the application has content to work with.
        docs_path = rag_cfg.get("docs_path")
        if not self._passages and isinstance(docs_path, str) and os.path.isdir(docs_path):
            LOG.info("RAG store empty – ingesting documents from %s", docs_path)
            try:
                self.ingest(docs_path)
            except Exception:  # pragma: no cover - defensive path
                LOG.exception("Automatic ingestion failed")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def query(self, query_text: str, top_k: int = 5) -> List[Dict[str, object]]:
        """Return the top ``top_k`` passages relevant to ``query_text``.

        The scoring strategy is intentionally simple: it tokenises the
        query and each stored passage, then scores passages by the number
        of overlapping tokens adjusted by the query length.  Only
        positive matches are returned.
        """

        if not self._passages:
            LOG.debug("RAG query requested but no passages are available")
            return []

        query_counts = self._tokenise(query_text)
        if not query_counts:
            LOG.debug("RAG query has no meaningful tokens")
            return []
        query_tokens = set(query_counts)
        total_query_terms = sum(query_counts.values())

        scores = []
        for passage in self._passages:
            passage_tokens = set(passage.tokens)
            overlap = query_tokens & passage_tokens
            if not overlap:
                continue
            # Score emphasises the proportion of the query covered plus a
            # small bonus for longer overlaps.
            coverage = sum(query_counts[token] for token in overlap) / max(total_query_terms, 1)
            bonus = min(len(overlap), 10) / 10.0
            score = coverage + 0.1 * bonus
            scores.append((score, passage))

        scores.sort(key=lambda item: item[0], reverse=True)
        top_passages = [
            {"text": passage.text, "source": passage.source, "score": round(score, 4)}
            for score, passage in scores[: max(top_k, 0)]
        ]
        return top_passages

    def ingest(self, path: str) -> None:
        """Ingest a directory tree or a single file into the RAG store."""

        if os.path.isdir(path):
            files = list(self._iter_text_files(path))
            if not files:
                LOG.warning("No supported text files found under %s", path)
                return
        elif os.path.isfile(path):
            files = [path]
        else:
            raise FileNotFoundError(f"Path not found: {path}")

        LOG.info("Ingesting %d file(s) into RAG store", len(files))
        new_passages: List[Passage] = []
        for file_path in files:
            try:
                text = self._read_text(file_path)
            except Exception:
                LOG.exception("Failed to read %s", file_path)
                continue

            for chunk in self._chunk_text(text):
                tokens = sorted(self._tokenise(chunk))
                if not tokens:
                    continue
                rel_path = os.path.relpath(file_path, start=os.getcwd())
                new_passages.append(Passage(text=chunk, source=rel_path, tokens=tokens))

        if not new_passages:
            LOG.warning("No passages produced during ingestion of %s", path)
            return

        # Remove any existing passages originating from files we just
        # processed to avoid stale duplicates.
        sources = {p.source for p in new_passages}
        self._passages = [p for p in self._passages if p.source not in sources]
        self._passages.extend(new_passages)
        self._save_store()
        LOG.info("Stored %d passages (total now %d)", len(new_passages), len(self._passages))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_store(self) -> None:
        if not os.path.exists(self.store_path):
            self._passages = []
            return
        try:
            with open(self.store_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            LOG.exception("Failed to load RAG store from %s", self.store_path)
            self._passages = []
            return
        self._passages = [Passage.from_dict(item) for item in data]
        LOG.info("Loaded %d passages from %s", len(self._passages), self.store_path)

    def _save_store(self) -> None:
        try:
            with open(self.store_path, "w", encoding="utf-8") as fh:
                json.dump([p.to_dict() for p in self._passages], fh, ensure_ascii=False, indent=2)
        except Exception:
            LOG.exception("Failed to save RAG store to %s", self.store_path)

    @staticmethod
    def _iter_text_files(directory: str) -> Iterable[str]:
        for root, _, files in os.walk(directory):
            for name in files:
                ext = os.path.splitext(name)[1].lower()
                if ext in TEXT_EXTENSIONS:
                    yield os.path.join(root, name)

    @staticmethod
    def _read_text(path: str) -> str:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.read()

    def _chunk_text(self, text: str) -> Iterable[str]:
        """Split ``text`` into overlapping character-based chunks."""

        cleaned = re.sub(r"\s+", " ", text).strip()
        if not cleaned:
            return []
        length = len(cleaned)
        if length <= self.chunk_size:
            return [cleaned]

        chunks: List[str] = []
        start = 0
        while start < length:
            end = min(start + self.chunk_size, length)
            chunk = cleaned[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end == length:
                break
            start = max(0, end - self.chunk_overlap)
        return chunks

    @staticmethod
    def _tokenise(text: str) -> Counter:
        tokens = re.findall(r"[\wÅÄÖåäö]+", text.lower())
        return Counter(tokens)


def load_config(path: str) -> Dict[str, object]:
    if not path or not os.path.exists(path):
        return {}
    if yaml is None:
        raise RuntimeError("PyYAML is required to load configuration files")
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Simple RAG ingestion tool")
    parser.add_argument("--ingest", metavar="PATH", help="File or directory to ingest into the RAG store")
    parser.add_argument("--config", default="config.yaml", help="Optional configuration file (YAML)")
    args = parser.parse_args(argv)

    cfg: Dict[str, object] = {}
    if args.config and os.path.exists(args.config):
        cfg = load_config(args.config)

    retriever = Retriever(cfg)
    retriever.ingest(args.ingest)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
