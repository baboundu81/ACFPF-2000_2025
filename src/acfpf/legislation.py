# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from acfpf.data.assemblee_legislation import (
    ASSEMBLY_SOURCE_PAGE,
    AssemblyLegislationError,
    AssemblyLegislativeDossier,
    AssemblyLegislativeEvent,
    load_assembly_dossiers,
)
from acfpf.data.senat_legislation import (
    SENATE_SOURCE_PAGE,
    SenateLegislationError,
    SenateLegislativeDossier,
    load_senate_dossiers,
)

DEFAULT_CACHE_PATH = Path.home() / ".cache" / "acfpf" / "assembly_legislation_17.zip"
DEFAULT_SENATE_CACHE_PATH = Path.home() / ".cache" / "acfpf" / "senat_dosleg.csv"


class LegislationError(RuntimeError):
    """Raised when no configured legislative source can be loaded."""


@dataclass(frozen=True)
class LegislativeEvent:
    date: str | None
    label: str
    code: str | None = None
    chamber: str | None = None
    source_id: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "date": self.date,
            "label": self.label,
            "code": self.code,
            "chamber": self.chamber,
            "source_id": self.source_id,
        }


@dataclass(frozen=True)
class LegislativeSourceRef:
    source_id: str
    label: str
    chamber: str
    official_url: str
    state: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "source_id": self.source_id,
            "label": self.label,
            "chamber": self.chamber,
            "official_url": self.official_url,
            "state": self.state,
        }


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
    sources: tuple[LegislativeSourceRef, ...] = ()
    themes: tuple[str, ...] = ()
    initial_date: str | None = None
    law_number: str | None = None
    current_chamber: str | None = None

    def as_dict(self, *, include_events: bool = True) -> dict[str, Any]:
        sources = self.sources or (
            LegislativeSourceRef(
                source_id=self.source_id,
                label=self.source_id,
                chamber=self.current_chamber or "",
                official_url=self.official_url,
            ),
        )
        payload: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "legislature": self.legislature,
            "procedure_code": self.procedure_code,
            "procedure_label": self.procedure_label,
            "status": self.status,
            "status_label": self.status_label,
            "current_stage": self.current_stage,
            "current_chamber": self.current_chamber,
            "last_activity": self.last_activity,
            "initial_date": self.initial_date,
            "law_number": self.law_number,
            "themes": list(self.themes),
            "official_url": self.official_url,
            "source_url": self.source_url,
            "source_id": self.source_id,
            "sources": [source.as_dict() for source in sources],
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
        preferred = list(
            dict.fromkeys(
                source.source_id for source in self.sources if source.source_id
            )
        )
        if not preferred:
            preferred = [self.source_id]
        if "legifrance" not in preferred:
            preferred.append("legifrance")
        return {
            "type": "legislative_dossier",
            "dossier_id": self.id,
            "title": self.title,
            "legislature": self.legislature,
            "procedure": self.procedure_label,
            "status": self.status,
            "status_label": self.status_label,
            "current_stage": self.current_stage,
            "current_chamber": self.current_chamber,
            "last_activity": self.last_activity,
            "official_urls": [source.official_url for source in self.sources] or [self.official_url],
            "preferred_source_ids": preferred,
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


def _canonical_title(value: str) -> str:
    normalized = _normalize(value)
    return re.sub(
        r"^(projet|proposition) de loi (constitutionnelle |organique )?",
        "",
        normalized,
    ).strip()


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


def _chamber_from_label(label: str | None) -> str | None:
    normalized = _normalize(label or "")
    if "commission mixte paritaire" in normalized:
        return "Commission mixte paritaire"
    if "assemblee nationale" in normalized or normalized.endswith(" an"):
        return "Assemblée nationale"
    if "senat" in normalized:
        return "Sénat"
    if "congres" in normalized:
        return "Congrès du Parlement"
    return None


def _status_from_assembly_events(events: tuple[AssemblyLegislativeEvent, ...]) -> tuple[str, str]:
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


def _status_from_senate_state(state: str | None) -> tuple[str, str]:
    normalized = _normalize(state or "")
    if not normalized:
        return "unknown", "Statut à vérifier"
    if "promulgue" in normalized:
        return "promulgated", "Promulgué"
    if any(
        token in normalized
        for token in ("non adopte", "caduc", "retire", "irrecevable", "non conforme")
    ):
        return "closed_without_law", "Clos sans promulgation"
    if normalized == "adopte" or "adoption definitive" in normalized:
        return "adopted", "Adopté"
    return "active", "En cours"


def _to_domain_assembly(dossier: AssemblyLegislativeDossier) -> LegislativeDossier:
    status, status_label = _status_from_assembly_events(dossier.events)
    current_event = None
    if dossier.events:
        dated = [event for event in dossier.events if event.date]
        current_event = max(dated, key=lambda item: item.date or "") if dated else dossier.events[-1]
    events = tuple(
        LegislativeEvent(
            date=event.date,
            label=event.label,
            code=event.code,
            chamber=_chamber_from_label(event.label),
            source_id="assemblee_nationale_open_data",
        )
        for event in dossier.events
    )
    dates = [event.date for event in dossier.events if event.date]
    return LegislativeDossier(
        id=dossier.uid,
        title=dossier.title,
        legislature=dossier.legislature,
        procedure_code=dossier.procedure_code,
        procedure_label=dossier.procedure_label,
        status=status,
        status_label=status_label,
        current_stage=current_event.label if current_event else None,
        current_chamber=_chamber_from_label(current_event.label) if current_event else None,
        last_activity=dossier.last_activity,
        initial_date=min(dates) if dates else None,
        official_url=dossier.official_url,
        source_url=ASSEMBLY_SOURCE_PAGE,
        source_id="assemblee_nationale_open_data",
        retrieved_at=dossier.retrieved_at,
        from_cache=dossier.from_cache,
        events=events,
        sources=(
            LegislativeSourceRef(
                source_id="assemblee_nationale_open_data",
                label="Assemblée nationale",
                chamber="Assemblée nationale",
                official_url=dossier.official_url,
            ),
        ),
    )


def _to_domain_senate(dossier: SenateLegislativeDossier) -> LegislativeDossier:
    status, status_label = _status_from_senate_state(dossier.state)
    events: list[LegislativeEvent] = []
    if dossier.constitutional_date:
        events.append(
            LegislativeEvent(
                date=dossier.constitutional_date,
                label=(
                    "Décision du Conseil constitutionnel"
                    + (f" : {dossier.constitutional_result}" if dossier.constitutional_result else "")
                ),
                code="CONSTITUTIONAL_COUNCIL",
                source_id="senat_open_data",
            )
        )
    if dossier.promulgation_date:
        events.append(
            LegislativeEvent(
                date=dossier.promulgation_date,
                label=(
                    "Promulgation"
                    + (f" — loi n° {dossier.law_number}" if dossier.law_number else "")
                ),
                code="PROMULGATION",
                source_id="senat_open_data",
            )
        )
    dates = [
        value
        for value in (
            dossier.initial_date,
            dossier.constitutional_date,
            dossier.promulgation_date,
        )
        if value
    ]
    return LegislativeDossier(
        id=dossier.uid,
        title=dossier.title,
        legislature="",
        procedure_code=None,
        procedure_label=dossier.type_label,
        status=status,
        status_label=status_label,
        current_stage=dossier.state,
        current_chamber=_chamber_from_label(dossier.state),
        last_activity=max(dates) if dates else None,
        initial_date=dossier.initial_date,
        law_number=dossier.law_number,
        official_url=dossier.official_url,
        source_url=SENATE_SOURCE_PAGE,
        source_id="senat_open_data",
        retrieved_at=dossier.retrieved_at,
        from_cache=dossier.from_cache,
        events=tuple(events),
        sources=(
            LegislativeSourceRef(
                source_id="senat_open_data",
                label="Sénat",
                chamber="Sénat",
                official_url=dossier.official_url,
                state=dossier.state,
            ),
        ),
        themes=dossier.themes,
    )


def _status_rank(status: str) -> int:
    return {
        "promulgated": 5,
        "adopted": 4,
        "closed_without_law": 4,
        "active": 2,
        "unknown": 1,
    }.get(status, 0)


def _merge_events(
    left: tuple[LegislativeEvent, ...], right: tuple[LegislativeEvent, ...]
) -> tuple[LegislativeEvent, ...]:
    unique: dict[tuple[Any, ...], LegislativeEvent] = {}
    for event in (*left, *right):
        key = (event.date, event.label, event.code, event.chamber, event.source_id)
        unique[key] = event
    return tuple(
        sorted(unique.values(), key=lambda event: (event.date or "", event.label))
    )


def _merge_sources(
    left: tuple[LegislativeSourceRef, ...], right: tuple[LegislativeSourceRef, ...]
) -> tuple[LegislativeSourceRef, ...]:
    result: dict[tuple[str, str], LegislativeSourceRef] = {}
    for source in (*left, *right):
        result[(source.source_id, source.official_url)] = source
    return tuple(result.values())


def _choose_status(left: LegislativeDossier, right: LegislativeDossier) -> LegislativeDossier:
    left_key = (
        _status_rank(left.status),
        left.source_id == "senat_open_data",
        left.last_activity or "",
    )
    right_key = (
        _status_rank(right.status),
        right.source_id == "senat_open_data",
        right.last_activity or "",
    )
    return right if right_key > left_key else left


def _merge_dossiers(left: LegislativeDossier, right: LegislativeDossier) -> LegislativeDossier:
    chosen_status = _choose_status(left, right)
    assembly = next(
        (
            item
            for item in (left, right)
            if item.source_id == "assemblee_nationale_open_data"
        ),
        left,
    )
    dates = [value for value in (left.last_activity, right.last_activity) if value]
    initial_dates = [value for value in (left.initial_date, right.initial_date) if value]
    retrieved = [value for value in (left.retrieved_at, right.retrieved_at) if value]
    return LegislativeDossier(
        id=assembly.id,
        title=assembly.title,
        legislature=assembly.legislature or right.legislature,
        procedure_code=assembly.procedure_code or right.procedure_code,
        procedure_label=assembly.procedure_label or right.procedure_label,
        status=chosen_status.status,
        status_label=chosen_status.status_label,
        current_stage=chosen_status.current_stage or assembly.current_stage,
        current_chamber=chosen_status.current_chamber or assembly.current_chamber,
        last_activity=max(dates) if dates else None,
        initial_date=min(initial_dates) if initial_dates else None,
        law_number=left.law_number or right.law_number,
        official_url=assembly.official_url,
        source_url=assembly.source_url,
        source_id=assembly.source_id,
        retrieved_at=max(retrieved) if retrieved else None,
        from_cache=left.from_cache and right.from_cache,
        events=_merge_events(left.events, right.events),
        sources=_merge_sources(left.sources, right.sources),
        themes=tuple(dict.fromkeys((*left.themes, *right.themes))),
    )


def _merge_inventory(dossiers: list[LegislativeDossier]) -> tuple[LegislativeDossier, ...]:
    merged: dict[str, LegislativeDossier] = {}
    for dossier in dossiers:
        key = _canonical_title(dossier.title)
        if key in merged:
            merged[key] = _merge_dossiers(merged[key], dossier)
        else:
            merged[key] = dossier
    return tuple(merged.values())


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
            for value in (
                dossier.title,
                dossier.procedure_label or "",
                dossier.current_stage or "",
                " ".join(dossier.themes),
            )
            if value
        )
    )
    title = _normalize(dossier.title)
    score = 0
    for keyword in search.keywords:
        if keyword in haystack:
            score += 10 if keyword in title else 3
    return score


class LegislationService:
    def __init__(
        self,
        *,
        cache_path: Path = DEFAULT_CACHE_PATH,
        senate_cache_path: Path = DEFAULT_SENATE_CACHE_PATH,
        loader: Callable[..., tuple[AssemblyLegislativeDossier, ...]] | None = None,
        senate_loader: Callable[..., tuple[SenateLegislativeDossier, ...]] | None = None,
    ) -> None:
        self.cache_path = cache_path
        self.senate_cache_path = senate_cache_path
        self.loader = loader or load_assembly_dossiers
        self.senate_loader = (
            load_senate_dossiers if loader is None and senate_loader is None else senate_loader
        )
        self._warnings: tuple[str, ...] = ()

    def warnings(self) -> tuple[str, ...]:
        return self._warnings

    def _all(self, *, refresh: bool = False) -> tuple[LegislativeDossier, ...]:
        items: list[LegislativeDossier] = []
        warnings: list[str] = []
        try:
            raw_assembly = self.loader(cache_path=self.cache_path, refresh=refresh)
            items.extend(_to_domain_assembly(item) for item in raw_assembly)
        except AssemblyLegislationError as exc:
            warnings.append(f"Assemblée nationale : {exc}")

        if self.senate_loader is not None:
            try:
                raw_senate = self.senate_loader(
                    cache_path=self.senate_cache_path,
                    refresh=refresh,
                )
                items.extend(_to_domain_senate(item) for item in raw_senate)
            except SenateLegislationError as exc:
                warnings.append(f"Sénat : {exc}")

        self._warnings = tuple(warnings)
        if not items and warnings:
            raise LegislationError(" ; ".join(warnings))
        return _merge_inventory(items)

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
            if any(
                source.source_id == "senat_open_data"
                and dossier_id == source.official_url.rsplit("/", 1)[-1].removesuffix(".html")
                for source in dossier.sources
            ):
                return dossier
        return None
