# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from acfpf.legislation import (
    LegislationService,
    LegislativeDossier,
    _normalize,
    _relevance,
    _status_matches,
    parse_legislative_search,
)
from acfpf.legislative_stages import LegislativeStage, classify_dossier_stage


@dataclass(frozen=True)
class LegislativeFacets:
    chambers: tuple[str, ...]
    stages: tuple[LegislativeStage, ...]
    themes: tuple[str, ...]
    text_types: tuple[str, ...]
    min_year: int | None
    max_year: int | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "chambers": list(self.chambers),
            "stages": [stage.as_dict() for stage in self.stages],
            "themes": list(self.themes),
            "text_types": list(self.text_types),
            "min_year": self.min_year,
            "max_year": self.max_year,
        }


@dataclass(frozen=True)
class LegislativeBrowseResult:
    results: tuple[LegislativeDossier, ...]
    facets: LegislativeFacets


def canonical_text_type(dossier: LegislativeDossier) -> str:
    """Return a stable coarse type suitable for user-facing filtering."""
    value = _normalize(" ".join((dossier.procedure_label or "", dossier.title)))
    if "proposition de loi" in value:
        return "Proposition de loi"
    if "projet de loi" in value:
        return "Projet de loi"
    if "resolution" in value:
        return "Résolution"
    if "convention" in value or "accord international" in value:
        return "Convention / accord"
    return dossier.procedure_label or "Autre"


def dossier_reference_year(dossier: LegislativeDossier) -> int | None:
    """Use the dossier start/deposit year, falling back to latest activity when absent."""
    value = dossier.initial_date or dossier.last_activity
    if not value or len(value) < 4 or not value[:4].isdigit():
        return None
    return int(value[:4])


def _facet_chamber(dossier: LegislativeDossier) -> str | None:
    if dossier.current_chamber:
        return dossier.current_chamber
    chambers = [source.chamber for source in dossier.sources if source.chamber]
    return chambers[0] if len(set(chambers)) == 1 and chambers else None


def _facets(dossiers: tuple[LegislativeDossier, ...]) -> LegislativeFacets:
    chambers = sorted(
        {value for dossier in dossiers if (value := _facet_chamber(dossier))},
        key=_normalize,
    )
    stages_by_code = {
        item.code: item
        for dossier in dossiers
        if (item := classify_dossier_stage(dossier)).code != "unknown"
    }
    stages = sorted(stages_by_code.values(), key=lambda item: _normalize(item.label))
    themes = sorted(
        {theme for dossier in dossiers for theme in dossier.themes if theme},
        key=_normalize,
    )
    text_types = sorted({canonical_text_type(dossier) for dossier in dossiers}, key=_normalize)
    years = [year for dossier in dossiers if (year := dossier_reference_year(dossier))]
    return LegislativeFacets(
        chambers=tuple(chambers),
        stages=tuple(stages),
        themes=tuple(themes),
        text_types=tuple(text_types),
        min_year=min(years) if years else None,
        max_year=max(years) if years else None,
    )


def _matches_value(actual: str | None, requested: str | None) -> bool:
    if not requested:
        return True
    return _normalize(actual or "") == _normalize(requested)


def _matches_theme(dossier: LegislativeDossier, theme: str | None) -> bool:
    if not theme:
        return True
    wanted = _normalize(theme)
    return any(_normalize(item) == wanted for item in dossier.themes)


def _matches_stage(dossier: LegislativeDossier, requested: str | None) -> bool:
    if not requested:
        return True
    return classify_dossier_stage(dossier).code == requested


def _matches_year(
    dossier: LegislativeDossier,
    from_year: int | None,
    to_year: int | None,
) -> bool:
    if from_year is None and to_year is None:
        return True
    year = dossier_reference_year(dossier)
    if year is None:
        return False
    if from_year is not None and year < from_year:
        return False
    return not (to_year is not None and year > to_year)


def browse_legislation(
    service: LegislationService,
    query: str = "",
    *,
    status: str | None = None,
    chamber: str | None = None,
    stage: str | None = None,
    theme: str | None = None,
    text_type: str | None = None,
    from_year: int | None = None,
    to_year: int | None = None,
    limit: int = 30,
    refresh: bool = False,
) -> LegislativeBrowseResult:
    """Search and facet one loaded legislative inventory."""
    if from_year is not None and to_year is not None and from_year > to_year:
        raise ValueError("L'année de début ne peut pas être postérieure à l'année de fin.")

    dossiers = service._all(refresh=refresh)
    search = parse_legislative_search(query, status=status)
    candidates: list[tuple[int, LegislativeDossier]] = []

    for dossier in dossiers:
        if not _status_matches(dossier.status, search.status):
            continue
        score = _relevance(dossier, search)
        if search.keywords and score == 0:
            continue
        if not _matches_value(_facet_chamber(dossier), chamber):
            continue
        if not _matches_stage(dossier, stage):
            continue
        if not _matches_theme(dossier, theme):
            continue
        if not _matches_value(canonical_text_type(dossier), text_type):
            continue
        if not _matches_year(dossier, from_year, to_year):
            continue
        candidates.append((score, dossier))

    candidates.sort(
        key=lambda item: (item[0], item[1].last_activity or "", item[1].title, item[1].id),
        reverse=True,
    )
    max_results = max(1, min(limit, 100))
    return LegislativeBrowseResult(
        results=tuple(dossier for _, dossier in candidates[:max_results]),
        facets=_facets(dossiers),
    )
