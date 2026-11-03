# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from acfpf.ai.legislation_query import LegislativeQueryPlan, LegislativeQueryPlanner
from acfpf.ai.provider import AIError
from acfpf.legislation import LegislationService, parse_legislative_search
from acfpf.legislation_browse import LegislativeBrowseResult, browse_legislation


@dataclass(frozen=True)
class AssistedLegislativeBrowseResult:
    browse: LegislativeBrowseResult
    original_query: str
    effective_query: str
    interpreted_plan: LegislativeQueryPlan | None
    planner_used: bool
    planner_warning: str | None
    effective_status: str
    effective_filters: dict[str, str | int | None]

    def as_meta_dict(self) -> dict[str, Any]:
        return {
            "original_query": self.original_query,
            "effective_query": self.effective_query,
            "planner_used": self.planner_used,
            "planner_warning": self.planner_warning,
            "interpreted_plan": (
                self.interpreted_plan.as_dict() if self.interpreted_plan is not None else None
            ),
            "effective_status": self.effective_status,
            "effective_filters": self.effective_filters,
        }


def _nonempty(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _explicit_filters(
    *,
    chamber: str | None,
    stage: str | None,
    theme: str | None,
    text_type: str | None,
    from_year: int | None,
    to_year: int | None,
) -> dict[str, str | int | None]:
    return {
        "chamber": _nonempty(chamber),
        "stage": _nonempty(stage),
        "theme": _nonempty(theme),
        "text_type": _nonempty(text_type),
        "from_year": from_year,
        "to_year": to_year,
    }


def _merge_filters(
    explicit: dict[str, str | int | None],
    plan: LegislativeQueryPlan,
) -> dict[str, str | int | None]:
    planned = {
        "chamber": plan.chamber,
        "stage": plan.stage,
        "theme": plan.theme,
        "text_type": plan.text_type,
        "from_year": plan.from_year,
        "to_year": plan.to_year,
    }
    return {
        key: explicit[key] if explicit[key] is not None else planned[key]
        for key in explicit
    }


def assisted_browse_legislation(
    service: LegislationService,
    query: str = "",
    *,
    planner: LegislativeQueryPlanner | None = None,
    assist: bool = True,
    status: str | None = None,
    chamber: str | None = None,
    stage: str | None = None,
    theme: str | None = None,
    text_type: str | None = None,
    from_year: int | None = None,
    to_year: int | None = None,
    limit: int = 30,
    refresh: bool = False,
) -> AssistedLegislativeBrowseResult:
    """Interpret a vague query, then run only the deterministic official-inventory search.

    Explicit filters supplied by the user always override planner suggestions. Any planner failure
    is non-fatal and falls back to the pre-existing deterministic query parser.
    """
    original_query = query.strip()
    explicit = _explicit_filters(
        chamber=chamber,
        stage=stage,
        theme=theme,
        text_type=text_type,
        from_year=from_year,
        to_year=to_year,
    )

    planned: LegislativeQueryPlan | None = None
    planner_warning: str | None = None
    effective_query = original_query
    effective_filters = explicit
    effective_status_arg = status

    if assist and planner is not None and original_query:
        try:
            inventory = browse_legislation(
                service,
                "",
                status="all",
                limit=1,
                refresh=refresh,
            )
            planned = planner.plan(original_query, inventory.facets)
            effective_query = planned.query
            effective_filters = _merge_filters(explicit, planned)
            if status is None and planned.status is not None:
                effective_status_arg = planned.status
        except AIError as exc:
            planner_warning = (
                "L'interprétation assistée n'a pas pu être utilisée ; "
                "la recherche déterministe d'origine a été conservée. "
                f"Détail : {exc}"
            )

    browse = browse_legislation(
        service,
        effective_query,
        status=effective_status_arg,
        chamber=effective_filters["chamber"],
        stage=effective_filters["stage"],
        theme=effective_filters["theme"],
        text_type=effective_filters["text_type"],
        from_year=effective_filters["from_year"],
        to_year=effective_filters["to_year"],
        limit=limit,
        refresh=refresh,
    )
    effective_status = parse_legislative_search(
        effective_query,
        status=effective_status_arg,
    ).status
    return AssistedLegislativeBrowseResult(
        browse=browse,
        original_query=original_query,
        effective_query=effective_query,
        interpreted_plan=planned,
        planner_used=planned is not None,
        planner_warning=planner_warning,
        effective_status=effective_status,
        effective_filters=effective_filters,
    )
