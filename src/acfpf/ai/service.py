# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from acfpf.ai.provider import (
    AIGroundingError,
    AIProviderNotConfigured,
    LLMProvider,
    ProviderRequest,
)
from acfpf.ai.registry import build_provider_from_env
from acfpf.cofog import CofogService
from acfpf.data.eurostat import EurostatError
from acfpf.macro import MacroService

SYSTEM_PROMPT = """Tu es le moteur d'analyse ACFPF.

Règles impératives :
- Réponds uniquement à partir du CONTEXTE_ACFPF fourni dans le message utilisateur.
- N'utilise aucune connaissance générale, aucun souvenir du modèle, aucune information du Web.
- Si le contexte ne suffit pas pour répondre correctement, retourne le statut `insufficient`.
- Ne présente jamais une causalité si le contexte ne contient qu'une corrélation ou une évolution descriptive.
- Distingue clairement fait observé, calcul simple et limite d'interprétation.
- Une baisse de dépense exprimée en points de PIB n'est pas automatiquement une économie en euros.
- Une décision, une prévision et une exécution ne sont jamais interchangeables.
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
    def __init__(
        self,
        provider: LLMProvider,
        macro_service: MacroService,
        cofog_service: CofogService | None = None,
    ) -> None:
        self.provider = provider
        self.macro_service = macro_service
        self.cofog_service = cofog_service

    def ask(self, question: str) -> GroundedAnswer:
        question = question.strip()
        if not question:
            raise ValueError("La question ne peut pas être vide.")
        if len(question) > 1500:
            raise ValueError("La question est trop longue (1500 caractères maximum).")

        context, citations = self._build_context()
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

    def _build_context(self) -> tuple[dict[str, Any], dict[str, Citation]]:
        dashboard = self.macro_service.dashboard().as_dict()
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
                "evidence_stage": "statistical_observation",
                "source_id": source_id,
                "values": series["values"],
            }

        cofog_context: dict[str, Any] | None = None
        cofog_error: str | None = None
        if self.cofog_service is not None:
            try:
                cofog = self.cofog_service.analysis().as_dict()
                source_id = f"S{len(citation_map) + 1}"
                citation_map[source_id] = Citation(
                    id=source_id,
                    dataset_code=cofog["dataset_code"],
                    label="Dépenses des administrations publiques par fonction (COFOG)",
                    source_url=cofog["source_url"],
                )
                cofog_context = {
                    "source_id": source_id,
                    "evidence_stage": "statistical_observation",
                    "unit": "% du PIB",
                    "changes_since_2000": cofog["changes"],
                    "interpretation_note": cofog["interpretation_note"],
                }
            except EurostatError as exc:
                cofog_error = str(exc)

        limitations = [
            "Le contexte actuel ne contient pas encore le texte intégral des lois, PAP, RAP, amendements ou rapports de contrôle.",
            "Les données COFOG permettent de localiser les variations par fonction, pas d'en attribuer la cause à une décision précise.",
        ]
        if cofog_error:
            limitations.append(f"Les données COFOG sont temporairement indisponibles : {cofog_error}")

        context = {
            "scope": "France, administrations publiques, période 2000-2025.",
            "macro_series": series_context,
            "cofog_functional_spending": cofog_context,
            "evidence_semantics": {
                "statistical_observation": "mesure constatée dans une source statistique",
                "forecast": "prévision ou autorisation, pas une dépense réalisée",
                "decision": "texte adopté ou décision juridique",
                "execution": "réalisation budgétaire constatée",
                "evaluation": "analyse a posteriori d'une politique ou de son exécution",
                "parliamentary_process": "proposition, amendement, débat ou vote à replacer dans son sort final",
            },
            "sources": [citation.as_dict() for citation in citation_map.values()],
            "limitations": limitations,
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
    cofog_service: CofogService | None = None,
) -> AnswerService | None:
    try:
        provider = build_provider_from_env()
    except AIProviderNotConfigured:
        return None
    return AnswerService(
        provider,
        macro_service or MacroService(),
        cofog_service or CofogService(),
    )
