# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from acfpf.ai.mistral import MistralProvider
from acfpf.ai.provider import (
    AIGroundingError,
    AIProviderNotConfigured,
    LLMProvider,
    ProviderRequest,
)
from acfpf.macro import MacroService

SYSTEM_PROMPT = """Tu es le moteur d'analyse ACFPF.

Règles impératives :
- Réponds uniquement à partir du CONTEXTE_ACFPF fourni dans le message utilisateur.
- N'utilise aucune connaissance générale, aucun souvenir du modèle, aucune information du Web.
- Si le contexte ne suffit pas pour répondre correctement, retourne le statut `insufficient`.
- Ne présente jamais une causalité si le contexte ne contient qu'une corrélation ou une évolution descriptive.
- Distingue clairement fait observé, calcul simple et limite d'interprétation.
- Toute réponse avec le statut `answered` doit citer au moins une source fournie dans le contexte.
- Les citations doivent utiliser exclusivement les identifiants de source autorisés (par exemple S1, S2).
- Réponds en français.
- Retourne uniquement un objet JSON valide avec exactement ces champs :
  `status` (`answered` ou `insufficient`), `answer` (string), `citations` (liste d'identifiants),
  `limitations` (liste de strings).
"""


@dataclass(frozen=True)
class Citation:
    id: str
    dataset_code: str
    label: str
    source_url: str

    def as_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "dataset_code": self.dataset_code,
            "label": self.label,
            "source_url": self.source_url,
        }


@dataclass(frozen=True)
class GroundedAnswer:
    status: str
    answer: str
    citations: tuple[Citation, ...]
    limitations: tuple[str, ...]
    provider: str
    model: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "answer": self.answer,
            "citations": [citation.as_dict() for citation in self.citations],
            "limitations": list(self.limitations),
            "provider": self.provider,
            "model": self.model,
        }


class AnswerService:
    def __init__(self, provider: LLMProvider, macro_service: MacroService) -> None:
        self.provider = provider
        self.macro_service = macro_service

    def ask(self, question: str) -> GroundedAnswer:
        question = question.strip()
        if not question:
            raise ValueError("La question ne peut pas être vide.")
        if len(question) > 1500:
            raise ValueError("La question est trop longue (1500 caractères maximum).")

        dashboard = self.macro_service.dashboard().as_dict()
        context, citations = self._build_macro_context(dashboard)
        allowed_ids = set(citations)

        request = ProviderRequest(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=(
                "QUESTION_UTILISATEUR:\n"
                f"{question}\n\n"
                "CONTEXTE_ACFPF (seule source d'information autorisée):\n"
                f"{json.dumps(context, ensure_ascii=False, separators=(',', ':'))}\n\n"
                "Retourne le JSON demandé."
            ),
        )
        raw = self.provider.complete_json(request)
        return self._validate_answer(raw, citations, allowed_ids)

    def _build_macro_context(
        self, dashboard: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Citation]]:
        citation_map: dict[str, Citation] = {}
        source_ids_by_dataset: dict[str, str] = {}

        for index, source in enumerate(dashboard.get("sources", []), start=1):
            source_id = f"S{index}"
            source_ids_by_dataset[source["dataset_code"]] = source_id
            citation_map[source_id] = Citation(
                id=source_id,
                dataset_code=source["dataset_code"],
                label=source["label"],
                source_url=source["source_url"],
            )

        main_source = source_ids_by_dataset.get("gov_10a_main")
        debt_source = source_ids_by_dataset.get("gov_10dd_edpt1")

        series_context: dict[str, Any] = {}
        for key, series in dashboard.get("series", {}).items():
            source_id = debt_source if key == "debt" else main_source
            series_context[key] = {
                "label": series["label"],
                "unit": series["unit"],
                "source_id": source_id,
                "values": series["values"],
            }

        context = {
            "scope": (
                "France, administrations publiques, séries macroéconomiques actuellement chargées "
                "dans ACFPF. Aucune donnée sectorielle détaillée n'est encore fournie à l'IA."
            ),
            "period": "2000-2025",
            "series": series_context,
            "sources": [citation.as_dict() for citation in citation_map.values()],
            "important_limit": (
                "Le contexte actuel ne permet pas de répondre aux questions détaillées sur "
                "l'éducation, la santé, la fiscalité par ménage, les retraites, la fraude ou les "
                "aides aux entreprises."
            ),
        }
        return context, citation_map

    def _validate_answer(
        self,
        raw: dict[str, Any],
        citations: dict[str, Citation],
        allowed_ids: set[str],
    ) -> GroundedAnswer:
        status = raw.get("status")
        answer = raw.get("answer")
        raw_citations = raw.get("citations")
        raw_limitations = raw.get("limitations")

        if status not in {"answered", "insufficient"}:
            raise AIGroundingError("Le modèle a retourné un statut invalide.")
        if not isinstance(answer, str) or not answer.strip():
            raise AIGroundingError("Le modèle a retourné une réponse vide ou invalide.")
        if not isinstance(raw_citations, list) or not all(
            isinstance(item, str) for item in raw_citations
        ):
            raise AIGroundingError("Le modèle a retourné des citations invalides.")
        if not isinstance(raw_limitations, list) or not all(
            isinstance(item, str) for item in raw_limitations
        ):
            raise AIGroundingError("Le modèle a retourné des limites invalides.")

        unknown = set(raw_citations).difference(allowed_ids)
        if unknown:
            raise AIGroundingError(
                f"Le modèle a cité des sources absentes du contexte: {sorted(unknown)}"
            )
        if status == "answered" and not raw_citations:
            raise AIGroundingError("Une réponse factuelle sans citation a été refusée.")

        unique_ids = tuple(dict.fromkeys(raw_citations))
        return GroundedAnswer(
            status=status,
            answer=answer.strip(),
            citations=tuple(citations[source_id] for source_id in unique_ids),
            limitations=tuple(item.strip() for item in raw_limitations if item.strip()),
            provider=self.provider.name,
            model=self.provider.model,
        )


def build_default_answer_service(
    macro_service: MacroService | None = None,
) -> AnswerService | None:
    try:
        provider = MistralProvider.from_env()
    except AIProviderNotConfigured:
        return None
    return AnswerService(provider, macro_service or MacroService())
