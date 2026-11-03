# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from acfpf.data.assemblee_legislation import (
    ASSEMBLY_SOURCE_PAGE,
    AssemblyLegislationError,
    AssemblyLegislativeDossier,
    AssemblyLegislativeEvent,
    load_assembly_dossiers,
)

DEFAULT_CACHE_PATH = Path.home() / ".cache" / "acfpf" / "assembly_legislation_17.zip"


class LegislationError(RuntimeError):
    """Raised when legislative dossiers cannot be searched or loaded."""


@dataclass(frozen=True)
class LegislativeEvent:
    date: str | None
    label: str
    code: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {"date": self.date, "label": self.label, "code": self.code}


@dataclass(frozen=True)
class LegislativeDossier:
    id: str
    title: str
    legislature: str
    procedure_code: str | None
    procedure_label: str | None
    status: str
    status_label: str
    current_stage: str | None
    last_activity: str | None
    official_url: str
    source_url: str
    source_id: str = "assemblee_nationale_open_data"
    retrieved_at: str | None = None
    from_cache: bool = False
    events: tuple[LegislativeEvent, ...] = ()

    def as_dict(self, *, include_events: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "legislature": self.legislature,
            "procedure_code": self.procedure_code,
            "procedure_label": self.procedure_label,
            "status": self.status,
            "status_label": self.status_label,
            "current_stage": self.current_stage,
            "last_activity": self.last_activity,
            "official_url": self.official_url,
            "source_url": self.source_url,
            "source_id": self.source_id,
            "retrieved_at": self.retrieved_at,
            "from_cache": self.from_cache,
        }
        if include_events:
            payload["events"] = [event.as_dict() for event in self.events]
        return payload

    def scope_context(self) -> dict[str, Any]:
        """Return trusted orientation metadata for a dossier-scoped AI investigation.

        These fields are not evidence by themselves: the AI must still open and cite official
        documents before making factual claims about the content of the text.
        """
        return {
            "type": "legislative_dossier",
            "dossier_id": self.id,
            "title": self.title,
            "legislature": self.legislature,
            "procedure": self.procedure_label,
            "status": self.status,
            "status_label": self.status_label,
            "current_stage": self.current_stage,
            "last_activity": self.last_activity,
            "official_url": self.official_url,
            "preferred_source_ids": [
                "assemblee_nationale_open_data",
                "senat_open_data",
                "legifrance",
            ],
        }


@dataclass(frozen=True)
class LegislativeSearch:
    query: str
    keywords: tuple[str, ...]
    status: str


STOPWORDS = {
    "a",
    "au",
    "aux",
    "avec",
    "ce",
    "ces",
    "dans",
    "de",
    "des",
    "discussion",
    "du",
    "examen",
    "en",
    "est",
    "et",
    "la",
    "le",
    "les",
    "loi",
    "lois",
    "me",
    "mon",
    "ont",
    "ete",
    "adopte",
    "adoptes",
    "adoptee",
    "adoptees",
    "assemblee",
    "promulgue",
    "promulgues",
    "promulguee",
    "promulguees",
    "recemment",
    "senat",
    "par",
    "parlement",
    "pour",
    "projet",
    "projets",
    "proposition",
    "propositions",
    "quel",
    "quelle",
    "quelles",
    "quels",
    "qui",
    "sont",
    "sur",
    "texte",
    "textes",
    "un",
    "une",
    "vote",
    "voter",
}


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", ascii_text.lower()).strip()


def parse_legislative_search(query: str, *, status: str | None = None) -> LegislativeSearch:
    normalized = _normalize(query)
    inferred_status = status or "active"
    if status is None:
        if any(token in normalized for token in ("promulgue", "promulgation")):
            inferred_status = "promulgated"
        elif any(token in normalized for token in ("adopte", "adoptee", "adoption")):
            inferred_status = "adopted_or_promulgated"
        elif any(token in normalized for token in ("rejete", "retire", "caduc")):
            inferred_status = "closed_without_law"
        elif any(
            token in normalized
            for token in ("en cours", "discussion", "examen", "actuellement", "parlement")
        ):
            inferred_status = "active"

    keywords = tuple(
        token
        for token in normalized.split()
        if len(token) >= 3 and token not in STOPWORDS and token not in {"cours", "actuellement"}
    )
    return LegislativeSearch(query=query, keywords=keywords, status=inferred_status)


def _status_from_events(events: tuple[AssemblyLegislativeEvent, ...]) -> tuple[str, str]:
    labels = " ".join(_normalize(event.label) for event in events)
    if any(token in labels for token in ("promulg", "journal officiel")):
        return "promulgated", "Promulgué"
    if any(
        token in labels
        for token in ("adoption definitive", "adopte definitivement", "texte definitif")
    ):
        return "adopted", "Adopté définitivement"
    if any(token in labels for token in ("retrait", "retire", "rejet definitif", "caduc")):
        return "closed_without_law", "Clos sans promulgation"
    return "active", "En cours"


def _to_domain(dossier: AssemblyLegislativeDossier) -> LegislativeDossier:
    status, status_label = _status_from_events(dossier.events)
    current = None
    if dossier.events:
        dated = [event for event in dossier.events if event.date]
        current = (max(dated, key=lambda item: item.date or "") if dated else dossier.events[-1]).label
    return LegislativeDossier(
        id=dossier.uid,
        title=dossier.title,
        legislature=dossier.legislature,
        procedure_code=dossier.procedure_code,
        procedure_label=dossier.procedure_label,
        status=status,
        status_label=status_label,
        current_stage=current,
        last_activity=dossier.last_activity,
        official_url=dossier.official_url,
        source_url=ASSEMBLY_SOURCE_PAGE,
        retrieved_at=dossier.retrieved_at,
        from_cache=dossier.from_cache,
        events=tuple(
            LegislativeEvent(date=event.date, label=event.label, code=event.code)
            for event in dossier.events
        ),
    )


def _status_matches(actual: str, requested: str) -> bool:
    if requested in {"all", ""}:
        return True
    if requested == "adopted_or_promulgated":
        return actual in {"adopted", "promulgated"}
    return actual == requested


def _relevance(dossier: LegislativeDossier, search: LegislativeSearch) -> int:
    if not search.keywords:
        return 0
    haystack = _normalize(
        " ".join(
            value
            for value in (dossier.title, dossier.procedure_label or "", dossier.current_stage or "")
            if value
        )
    )
    score = 0
    for keyword in search.keywords:
        if keyword in haystack:
            score += 10 if keyword in _normalize(dossier.title) else 3
    return score


class LegislationService:
    def __init__(
        self,
        *,
        cache_path: Path = DEFAULT_CACHE_PATH,
        loader: Callable[..., tuple[AssemblyLegislativeDossier, ...]] = load_assembly_dossiers,
    ) -> None:
        self.cache_path = cache_path
        self.loader = loader

    def _all(self, *, refresh: bool = False) -> tuple[LegislativeDossier, ...]:
        try:
            raw = self.loader(cache_path=self.cache_path, refresh=refresh)
        except AssemblyLegislationError as exc:
            raise LegislationError(str(exc)) from exc
        return tuple(_to_domain(item) for item in raw)

    def search(
        self,
        query: str = "",
        *,
        status: str | None = None,
        limit: int = 20,
        refresh: bool = False,
    ) -> tuple[LegislativeDossier, ...]:
        search = parse_legislative_search(query, status=status)
        candidates: list[tuple[int, LegislativeDossier]] = []
        for dossier in self._all(refresh=refresh):
            if not _status_matches(dossier.status, search.status):
                continue
            score = _relevance(dossier, search)
            if search.keywords and score == 0:
                continue
            candidates.append((score, dossier))

        candidates.sort(
            key=lambda item: (item[0], item[1].last_activity or "", item[1].title),
            reverse=True,
        )
        return tuple(dossier for _, dossier in candidates[: max(1, min(limit, 100))])

    def get(self, dossier_id: str, *, refresh: bool = False) -> LegislativeDossier | None:
        wanted = dossier_id.strip()
        if not wanted:
            return None
        for dossier in self._all(refresh=refresh):
            if dossier.id == wanted:
                return dossier
        return None
