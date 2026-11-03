# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from acfpf.ai.provider import AIGroundingError, AIProviderNotConfigured, LLMProvider, ProviderRequest
from acfpf.ai.registry import build_provider_from_env
from acfpf.legislation_browse import LegislativeFacets

MAX_REFINED_QUERY_CHARS = 200
ALLOWED_STATUSES = {"", "active", "adopted_or_promulgated", "closed_without_law", "all"}
ALLOWED_STAGES = {
    "",
    "deposit",
    "committee",
    "plenary",
    "shuttle",
    "cmp",
    "congress",
    "constitutional_review",
    "adopted",
    "promulgated",
    "closed",
}

LEGISLATIVE_QUERY_PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "maxLength": MAX_REFINED_QUERY_CHARS},
        "status": {"type": "string", "enum": sorted(ALLOWED_STATUSES)},
        "chamber": {"type": "string"},
        "stage": {"type": "string", "enum": sorted(ALLOWED_STAGES)},
        "theme": {"type": "string"},
        "text_type": {"type": "string"},
        "from_year": {"type": "integer"},
        "to_year": {"type": "integer"},
    },
    "required": [
        "query",
        "status",
        "chamber",
        "stage",
        "theme",
        "text_type",
        "from_year",
        "to_year",
    ],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """Tu traduis une recherche citoyenne approximative en critères de recherche ACFPF.

Tu NE recherches PAS les lois toi-même et tu ne dois JAMAIS identifier, nommer ou proposer un dossier.
Tu ne dois retourner ni URL, ni identifiant, ni titre de texte, ni liste de candidats.
Le backend appliquera tes critères à un inventaire officiel déjà chargé depuis l'Assemblée nationale et le Sénat.

Règles :
- `query` contient seulement quelques termes neutres utiles pour retrouver les métadonnées officielles.
- Les valeurs de `chamber`, `stage`, `theme` et `text_type` doivent venir exactement de AVAILABLE_FILTERS.
- `status` doit utiliser une valeur autorisée fournie.
- Utilise une chaîne vide si un filtre n'est pas justifié.
- Utilise 0 pour une année non utilisée.
- N'invente aucune information factuelle sur un texte.
- Si la demande est trop vague, conserve une requête courte et laisse les filtres vides plutôt que d'inventer.
- Réponds uniquement selon le schéma JSON imposé.
"""


@dataclass(frozen=True)
class LegislativeQueryPlan:
    query: str
    status: str | None = None
    chamber: str | None = None
    stage: str | None = None
    theme: str | None = None
    text_type: str | None = None
    from_year: int | None = None
    to_year: int | None = None

    def as_dict(self) -> dict[str, str | int | None]:
        return {
            "query": self.query,
            "status": self.status,
            "chamber": self.chamber,
            "stage": self.stage,
            "theme": self.theme,
            "text_type": self.text_type,
            "from_year": self.from_year,
            "to_year": self.to_year,
        }


class LegislativeQueryPlanner:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    def plan(self, user_query: str, facets: LegislativeFacets) -> LegislativeQueryPlan:
        query = user_query.strip()
        if not query:
            raise ValueError("La recherche à interpréter ne peut pas être vide.")

        state = {
            "USER_QUERY": query,
            "AVAILABLE_FILTERS": {
                "statuses": sorted(ALLOWED_STATUSES - {""}),
                "chambers": list(facets.chambers),
                "stages": [item.as_dict() for item in facets.stages],
                "themes": list(facets.themes),
                "text_types": list(facets.text_types),
                "min_year": facets.min_year,
                "max_year": facets.max_year,
            },
        }
        raw = self.provider.complete_json(
            ProviderRequest(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=json.dumps(state, ensure_ascii=False, separators=(",", ":")),
                response_schema=LEGISLATIVE_QUERY_PLAN_SCHEMA,
                response_schema_name="acfpf_legislative_query_plan",
            )
        )
        return self._validate(raw, facets)

    @staticmethod
    def _validate(raw: dict[str, Any], facets: LegislativeFacets) -> LegislativeQueryPlan:
        expected = set(LEGISLATIVE_QUERY_PLAN_SCHEMA["required"])
        if set(raw) != expected:
            raise AIGroundingError("Le planner a retourné des champs de recherche non autorisés.")

        query = raw.get("query")
        if not isinstance(query, str) or len(query.strip()) > MAX_REFINED_QUERY_CHARS:
            raise AIGroundingError("Le planner a retourné une requête affinée invalide.")

        def validated_string(field: str, allowed: set[str] | tuple[str, ...]) -> str | None:
            value = raw.get(field)
            if not isinstance(value, str):
                raise AIGroundingError(f"Le filtre {field} retourné par le planner est invalide.")
            value = value.strip()
            if not value:
                return None
            if value not in allowed:
                raise AIGroundingError(
                    f"Le planner a inventé une valeur non disponible pour le filtre {field}."
                )
            return value

        status = validated_string("status", ALLOWED_STATUSES)
        chamber = validated_string("chamber", facets.chambers)
        stage = validated_string("stage", tuple(item.code for item in facets.stages))
        theme = validated_string("theme", facets.themes)
        text_type = validated_string("text_type", facets.text_types)

        def validated_year(field: str) -> int | None:
            value = raw.get(field)
            if not isinstance(value, int):
                raise AIGroundingError(f"Le filtre {field} retourné par le planner est invalide.")
            if value == 0:
                return None
            if facets.min_year is not None and value < facets.min_year:
                raise AIGroundingError("Le planner a retourné une année hors de l'inventaire chargé.")
            if facets.max_year is not None and value > facets.max_year:
                raise AIGroundingError("Le planner a retourné une année hors de l'inventaire chargé.")
            return value

        from_year = validated_year("from_year")
        to_year = validated_year("to_year")
        if from_year is not None and to_year is not None and from_year > to_year:
            raise AIGroundingError("Le planner a retourné une période inversée.")

        return LegislativeQueryPlan(
            query=query.strip(),
            status=status,
            chamber=chamber,
            stage=stage,
            theme=theme,
            text_type=text_type,
            from_year=from_year,
            to_year=to_year,
        )


def build_default_legislative_query_planner() -> LegislativeQueryPlanner | None:
    try:
        provider = build_provider_from_env()
    except AIProviderNotConfigured:
        return None
    return LegislativeQueryPlanner(provider)
