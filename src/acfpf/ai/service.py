# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import json
from collections.abc import Iterator
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
from acfpf.live_research import LiveOfficialResearch, LiveResearchError
from acfpf.macro import MacroService

MAX_RESEARCH_STEPS = 14
MAX_QUESTION_CHARS = 1500

SYSTEM_PROMPT = """Tu es l'agent de recherche ACFPF.

Objectif : répondre à une question sur les finances publiques françaises à partir de données ACFPF et,
si nécessaire, d'une recherche LIVE limitée aux sources officielles autorisées par le backend.

Règles impératives :
- N'utilise jamais ta connaissance pré-entraînée comme preuve factuelle.
- Les titres et URL issus d'une recherche ne sont PAS des preuves : il faut ouvrir puis lire le document.
- Seuls les éléments présents dans EVIDENCE_AVAILABLE peuvent être cités dans la réponse finale.
- Si une question demande une cause, une réforme ou une décision et que les preuves disponibles ne suffisent pas,
  continue la recherche plutôt que d'inventer.
- Une décision, une prévision, une exécution et une évaluation ne sont pas interchangeables.
- Une baisse en points de PIB n'est pas automatiquement une économie en euros, en effectifs ou en niveau de service.
- Un amendement proposé ou rejeté n'est pas une décision applicable.
- Ne transforme jamais une corrélation en causalité.
- Si la recherche ne permet pas de conclure, réponds avec `status=insufficient`.
- Réponds en français.

À chaque tour, retourne UN SEUL objet JSON correspondant exactement à l'une des actions suivantes :

1. Rechercher des URL officielles :
{"action":"search","query":"...","source_ids":["budget_gouv","legifrance"],"reason":"..."}

2. Ouvrir une URL officielle :
{"action":"open","url":"https://...","reason":"..."}

3. Lire une autre unité d'un document déjà ouvert :
{"action":"read","document_id":"D1","unit":2,"reason":"..."}

4. Répondre :
{"action":"answer","status":"answered|insufficient","answer":"...","citations":["S1","E1"],"limitations":["..."]}

Les `source_ids` de search doivent venir de ALLOWED_SOURCES. Une citation finale inconnue sera rejetée.
"""


@dataclass(frozen=True)
class Citation:
    id: str
    dataset_code: str
    label: str
    source_url: str
    evidence_stage: str | None = None
    evidence_id: str | None = None
    locator: str | None = None
    source_id: str | None = None
    retrieved_at: str | None = None
    sha256: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "id": self.id,
            "dataset_code": self.dataset_code,
            "label": self.label,
            "source_url": self.source_url,
            "evidence_stage": self.evidence_stage,
            "evidence_id": self.evidence_id,
            "locator": self.locator,
            "source_id": self.source_id,
            "retrieved_at": self.retrieved_at,
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class GroundedAnswer:
    status: str
    answer: str
    citations: tuple[Citation, ...]
    limitations: tuple[str, ...]
    provider: str
    model: str
    research: tuple[dict[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "answer": self.answer,
            "citations": [citation.as_dict() for citation in self.citations],
            "limitations": list(self.limitations),
            "provider": self.provider,
            "model": self.model,
            "research": list(self.research),
        }


@dataclass(frozen=True)
class AgentEvent:
    type: str
    payload: dict[str, Any]
    answer: GroundedAnswer | None = None

    def as_dict(self) -> dict[str, Any]:
        if self.type == "answer" and self.answer is not None:
            return {"type": "answer", "answer": self.answer.as_dict()}
        return {"type": self.type, **self.payload}


class AnswerService:
    def __init__(
        self,
        provider: LLMProvider,
        macro_service: MacroService,
        cofog_service: CofogService | None = None,
        live_research: LiveOfficialResearch | None = None,
    ) -> None:
        self.provider = provider
        self.macro_service = macro_service
        self.cofog_service = cofog_service
        self.live_research = live_research

    def ask(self, question: str) -> GroundedAnswer:
        final: GroundedAnswer | None = None
        for event in self.iter_ask(question):
            if event.answer is not None:
                final = event.answer
        if final is None:
            raise AIGroundingError("La recherche n'a produit aucune réponse finale.")
        return final

    def iter_ask(self, question: str) -> Iterator[AgentEvent]:
        question = question.strip()
        if not question:
            raise ValueError("La question ne peut pas être vide.")
        if len(question) > MAX_QUESTION_CHARS:
            raise ValueError(f"La question est trop longue ({MAX_QUESTION_CHARS} caractères maximum).")

        research = self.live_research.spawn() if self.live_research is not None else None
        numeric_context, citations = self._build_numeric_context()
        evidence: dict[str, dict[str, Any]] = {}
        search_results: list[dict[str, Any]] = []
        documents: dict[str, dict[str, Any]] = {}
        research_trace: list[dict[str, Any]] = []
        read_units: dict[tuple[str, int], str] = {}
        evidence_counter = 0

        yield AgentEvent(
            "started",
            {
                "message": "Préparation des données et des sources officielles",
                "allowed_source_count": len(research.source_catalog()) if research else 0,
            },
        )

        for step_number in range(1, MAX_RESEARCH_STEPS + 1):
            state = {
                "QUESTION": question,
                "NUMERIC_CONTEXT": numeric_context,
                "ALLOWED_SOURCES": research.source_catalog() if research else [],
                "SEARCH_RESULTS": search_results[-24:],
                "OPEN_DOCUMENTS": list(documents.values()),
                "EVIDENCE_AVAILABLE": evidence,
                "RESEARCH_STEP": step_number,
                "RESEARCH_STEP_LIMIT": MAX_RESEARCH_STEPS,
            }
            raw = self.provider.complete_json(
                ProviderRequest(
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=json.dumps(state, ensure_ascii=False, separators=(",", ":")),
                )
            )
            action = raw.get("action")

            if action == "search":
                if research is None:
                    yield AgentEvent(
                        "notice",
                        {"message": "La recherche live n'est pas disponible ; réponse sur données seules."},
                    )
                    continue
                query = raw.get("query")
                source_ids = raw.get("source_ids")
                reason = raw.get("reason", "")
                if not isinstance(query, str) or not query.strip():
                    raise AIGroundingError("L'agent a demandé une recherche sans requête valide.")
                if not isinstance(source_ids, list) or not all(
                    isinstance(item, str) for item in source_ids
                ):
                    raise AIGroundingError("L'agent a demandé des sources de recherche invalides.")
                try:
                    results = research.search(query, source_ids=source_ids)
                except LiveResearchError as exc:
                    yield AgentEvent(
                        "notice",
                        {"message": str(exc), "action": "search", "query": query},
                    )
                    continue
                public_results = [item.as_dict() for item in results]
                search_results.extend(public_results)
                trace_item = {
                    "type": "search",
                    "query": query,
                    "source_ids": source_ids,
                    "result_count": len(public_results),
                    "reason": reason,
                }
                research_trace.append(trace_item)
                yield AgentEvent("search", trace_item)
                continue

            if action == "open":
                if research is None:
                    continue
                url = raw.get("url")
                reason = raw.get("reason", "")
                if not isinstance(url, str) or not url.startswith("https://"):
                    raise AIGroundingError("L'agent a demandé une URL invalide.")
                try:
                    document = research.open(url)
                except LiveResearchError as exc:
                    yield AgentEvent(
                        "notice",
                        {"message": str(exc), "action": "open", "url": url},
                    )
                    continue
                documents[document.document_id] = document.metadata()
                first_unit = document.units[0]
                key = (document.document_id, first_unit.index)
                evidence_counter += 1
                evidence_id = f"E{evidence_counter}"
                read_units[key] = evidence_id
                evidence[evidence_id] = self._live_evidence_payload(document, first_unit)
                source = research.sources[document.source_id]
                citations[evidence_id] = Citation(
                    id=evidence_id,
                    dataset_code=document.document_id,
                    label=document.title,
                    source_url=document.url,
                    evidence_stage=(source.evidence_stages[0] if len(source.evidence_stages) == 1 else None),
                    evidence_id=evidence_id,
                    locator=first_unit.locator,
                    source_id=document.source_id,
                    retrieved_at=document.retrieved_at,
                    sha256=document.sha256,
                )
                trace_item = {
                    "type": "open",
                    "document_id": document.document_id,
                    "source_id": document.source_id,
                    "title": document.title,
                    "url": document.url,
                    "unit_count": len(document.units),
                    "evidence_id": evidence_id,
                    "locator": first_unit.locator,
                    "reason": reason,
                }
                research_trace.append(trace_item)
                yield AgentEvent("open", trace_item)
                continue

            if action == "read":
                if research is None:
                    continue
                document_id = raw.get("document_id")
                unit_index = raw.get("unit")
                reason = raw.get("reason", "")
                if not isinstance(document_id, str) or not isinstance(unit_index, int):
                    raise AIGroundingError("L'agent a demandé une lecture de document invalide.")
                key = (document_id, unit_index)
                if key in read_units:
                    evidence_id = read_units[key]
                    item = evidence[evidence_id]
                else:
                    try:
                        unit = research.read(document_id, unit_index)
                        document = research.document(document_id)
                    except LiveResearchError as exc:
                        yield AgentEvent(
                            "notice",
                            {"message": str(exc), "action": "read", "document_id": document_id},
                        )
                        continue
                    evidence_counter += 1
                    evidence_id = f"E{evidence_counter}"
                    read_units[key] = evidence_id
                    item = self._live_evidence_payload(document, unit)
                    evidence[evidence_id] = item
                    source = research.sources[document.source_id]
                    citations[evidence_id] = Citation(
                        id=evidence_id,
                        dataset_code=document.document_id,
                        label=document.title,
                        source_url=document.url,
                        evidence_stage=(source.evidence_stages[0] if len(source.evidence_stages) == 1 else None),
                        evidence_id=evidence_id,
                        locator=unit.locator,
                        source_id=document.source_id,
                        retrieved_at=document.retrieved_at,
                        sha256=document.sha256,
                    )
                trace_item = {
                    "type": "read",
                    "document_id": document_id,
                    "evidence_id": evidence_id,
                    "locator": item["locator"],
                    "reason": reason,
                }
                research_trace.append(trace_item)
                yield AgentEvent("read", trace_item)
                continue

            if action == "answer":
                answer = self._validate_answer(raw, citations, research_trace=research_trace)
                yield AgentEvent("answer", {}, answer=answer)
                return

            raise AIGroundingError(f"L'agent a retourné une action inconnue : {action!r}")

        answer = GroundedAnswer(
            status="insufficient",
            answer=(
                "La recherche a atteint sa limite de sécurité avant de réunir suffisamment de preuves "
                "pour produire une réponse fiable."
            ),
            citations=(),
            limitations=(
                f"Limite de {MAX_RESEARCH_STEPS} étapes de recherche atteinte.",
                "Reformuler ou préciser la question peut réduire le périmètre de recherche.",
            ),
            provider=self.provider.name,
            model=self.provider.model,
            research=tuple(research_trace),
        )
        yield AgentEvent("answer", {}, answer=answer)

    def _build_numeric_context(self) -> tuple[dict[str, Any], dict[str, Citation]]:
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
                evidence_stage="statistical_observation",
                source_id="eurostat",
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

        cofog_context: dict[str, Any] | None = None
        if self.cofog_service is not None:
            try:
                cofog = self.cofog_service.analysis().as_dict()
                source_id = f"S{len(citation_map) + 1}"
                citation_map[source_id] = Citation(
                    id=source_id,
                    dataset_code=cofog["dataset_code"],
                    label="Dépenses des administrations publiques par fonction (COFOG)",
                    source_url=cofog["source_url"],
                    evidence_stage="statistical_observation",
                    source_id="eurostat",
                )
                cofog_context = {
                    "source_id": source_id,
                    "unit": "% du PIB",
                    "changes_since_2000": cofog["changes"],
                    "interpretation_note": cofog["interpretation_note"],
                }
            except EurostatError:
                cofog_context = None

        return (
            {
                "scope": "France, administrations publiques, période 2000-2025.",
                "macro_series": series_context,
                "cofog_functional_spending": cofog_context,
                "evidence_semantics": {
                    "statistical_observation": "mesure statistique constatée",
                    "forecast": "prévision ou autorisation, pas une exécution",
                    "decision": "texte adopté ou décision juridique",
                    "execution": "réalisation budgétaire constatée",
                    "evaluation": "analyse a posteriori",
                    "parliamentary_process": "travail parlementaire dont le sort final doit être vérifié",
                },
            },
            citation_map,
        )

    @staticmethod
    def _live_evidence_payload(document: Any, unit: Any) -> dict[str, Any]:
        return {
            "document_id": document.document_id,
            "source_id": document.source_id,
            "title": document.title,
            "url": document.url,
            "retrieved_at": document.retrieved_at,
            "sha256": document.sha256,
            "locator": unit.locator,
            "text": unit.text,
        }

    def _validate_answer(
        self,
        raw: dict[str, Any],
        citations: dict[str, Citation],
        *,
        research_trace: list[dict[str, Any]],
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

        unknown = set(raw_citations).difference(citations)
        if unknown:
            raise AIGroundingError(
                f"Le modèle a cité des preuves qui n'ont pas été lues par ACFPF : {sorted(unknown)}"
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
            research=tuple(research_trace),
        )


def build_default_answer_service(
    macro_service: MacroService | None = None,
    cofog_service: CofogService | None = None,
    live_research: LiveOfficialResearch | None = None,
) -> AnswerService | None:
    try:
        provider = build_provider_from_env()
    except AIProviderNotConfigured:
        return None
    return AnswerService(
        provider,
        macro_service or MacroService(),
        cofog_service or CofogService(),
        live_research or LiveOfficialResearch(),
    )
