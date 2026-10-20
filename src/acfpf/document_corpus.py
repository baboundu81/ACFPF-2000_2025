# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from acfpf.data.documents import (
    DocumentFetchError,
    fetch_official_document_text,
    split_document_text,
)
from acfpf.evidence import EvidenceChunk, EvidenceRef
from acfpf.evidence_catalog import load_evidence_documents

WORD_RE = re.compile(r"[a-z0-9]{3,}")
STOPWORDS = {
    "avec",
    "dans",
    "des",
    "les",
    "une",
    "pour",
    "par",
    "sur",
    "que",
    "qui",
    "aux",
    "est",
    "sont",
    "ont",
    "plus",
    "moins",
    "entre",
    "depuis",
    "cette",
    "cela",
    "comme",
    "leur",
    "leurs",
    "nous",
    "vous",
    "mais",
    "donc",
    "quoi",
    "comment",
    "pourquoi",
    "france",
    "francais",
    "francaise",
}


@dataclass(frozen=True)
class CorpusSearch:
    chunks: tuple[EvidenceChunk, ...]
    unavailable_documents: tuple[str, ...] = ()


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _tokens(text: str) -> list[str]:
    return [token for token in WORD_RE.findall(_normalize(text)) if token not in STOPWORDS]


def _score(question_tokens: list[str], text: str) -> int:
    if not question_tokens:
        return 0
    normalized = _normalize(text)
    score = sum(normalized.count(token) for token in set(question_tokens))
    phrase = " ".join(question_tokens)
    if phrase and phrase in normalized:
        score += 5
    return score


class OfficialDocumentCorpus:
    """Small local corpus populated only from explicitly allow-listed official URLs."""

    def __init__(
        self,
        *,
        cache_dir: Path | None = None,
        catalog_path: str | Path = "config/evidence_documents.yml",
    ) -> None:
        self.cache_dir = cache_dir or Path.home() / ".cache" / "acfpf" / "documents_v1"
        self.catalog_path = Path(catalog_path)

    def _cache_path(self, evidence: EvidenceRef) -> Path:
        safe_id = hashlib.sha256(evidence.id.encode("utf-8")).hexdigest()[:16]
        return self.cache_dir / f"{safe_id}.json"

    def _load_document(
        self, evidence: EvidenceRef, *, refresh: bool = False
    ) -> list[EvidenceChunk]:
        cache_path = self._cache_path(evidence)
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        if cache_path.exists() and not refresh:
            try:
                payload = json.loads(cache_path.read_text("utf-8"))
                return self._chunks_from_cache(evidence, payload)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                pass

        try:
            text = fetch_official_document_text(evidence.source_url)
            parts = split_document_text(text)
            payload = {
                "schema_version": 1,
                "evidence_id": evidence.id,
                "retrieved_at": datetime.now(UTC).isoformat(),
                "chunks": parts,
            }
            cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            return self._chunks_from_cache(evidence, payload)
        except DocumentFetchError:
            if cache_path.exists():
                try:
                    payload = json.loads(cache_path.read_text("utf-8"))
                    return self._chunks_from_cache(evidence, payload)
                except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                    pass
            raise

    @staticmethod
    def _chunks_from_cache(evidence: EvidenceRef, payload: dict) -> list[EvidenceChunk]:
        if payload.get("schema_version") != 1 or payload.get("evidence_id") != evidence.id:
            raise ValueError("Incompatible document cache")
        raw_chunks = payload.get("chunks")
        if not isinstance(raw_chunks, list):
            raise TypeError("Invalid document cache")
        return [
            EvidenceChunk(id=f"{evidence.id}#{index:04d}", evidence=evidence, text=text)
            for index, text in enumerate(raw_chunks, start=1)
            if isinstance(text, str) and text.strip()
        ]

    def search(self, question: str, *, limit: int = 5, refresh: bool = False) -> CorpusSearch:
        question_tokens = _tokens(question)
        scored: list[tuple[int, EvidenceChunk]] = []
        unavailable: list[str] = []

        for evidence in load_evidence_documents(self.catalog_path):
            if evidence.metadata.get("status") != "seed":
                continue
            try:
                chunks = self._load_document(evidence, refresh=refresh)
            except DocumentFetchError:
                unavailable.append(evidence.id)
                continue

            for chunk in chunks:
                score = _score(question_tokens, chunk.text)
                if score > 0:
                    scored.append((score, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        return CorpusSearch(
            chunks=tuple(chunk for _, chunk in scored[:limit]),
            unavailable_documents=tuple(unavailable),
        )
