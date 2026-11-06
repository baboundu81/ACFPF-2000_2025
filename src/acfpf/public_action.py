# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors
"""A sourced public-action lifecycle, without inferred law-to-budget links.

Known dossier events can document parliamentary *process*. They do not make
the legal norm, financing or outcomes verifiable without separate evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from acfpf.legislation import LegislativeDossier

STAGES: tuple[tuple[str, str], ...] = (
    ("proposal", "Proposition ou projet"),
    ("parliamentary_process", "Parcours parlementaire"),
    ("constitutional_review", "Contrôle constitutionnel"),
    ("promulgation", "Promulgation"),
    ("applicable_law", "Texte applicable"),
    ("regulatory_application", "Textes d'application"),
    ("financing_plan", "Financement prévu"),
    ("budget_authorization", "Budget voté"),
    ("budget_execution", "Exécution budgétaire"),
    ("outcome_indicators", "Résultats mesurés"),
    ("official_evaluation", "Évaluations officielles"),
)


@dataclass(frozen=True)
class PublicActionEvidence:
    category: str
    kind: str
    date: str | None
    label: str
    source_id: str
    source_url: str
    proof_level: str = "official_metadata"

    def as_dict(self) -> dict[str, Any]:
        return {
            "category": self.category, "kind": self.kind,
            "date": self.date, "label": self.label,
            "source_id": self.source_id, "source_url": self.source_url,
            "proof_level": self.proof_level,
            "normative_text_verified": False,
        }


def public_action_coverage(dossier: LegislativeDossier) -> dict[str, Any]:
    """Map exact source metadata to lifecycle stages, never filling missing stages."""
    urls: dict[str, str] = {}
    for source in dossier.sources:
        if (
            source.source_id in {"assemblee_nationale_open_data", "senat_open_data"}
            and source.official_url.startswith("https://")
        ):
            urls[source.source_id] = source.official_url
    if (
        not urls and dossier.source_id in {"assemblee_nationale_open_data", "senat_open_data"}
        and dossier.official_url.startswith("https://")
    ):
        urls[dossier.source_id] = dossier.official_url

    evidence: list[PublicActionEvidence] = []
    if dossier.initial_date and dossier.source_id in urls:
        evidence.append(PublicActionEvidence(
            category="proposal", kind="dossier_date",
            date=dossier.initial_date, label="Début ou dépôt du dossier",
            source_id=dossier.source_id, source_url=urls[dossier.source_id],
        ))

    for event in dossier.events:
        if event.source_id not in urls:
            continue
        if event.source_id == "senat_open_data" and event.code == "PROMULGATION":
            category = "promulgation"
        elif event.source_id == "senat_open_data" and event.code == "CONSTITUTIONAL_COUNCIL":
            category = "constitutional_review"
        else:
            category = "parliamentary_process"
        evidence.append(PublicActionEvidence(
            category=category, kind=event.code or "unclassified_event",
            date=event.date, label=event.label,
            source_id=event.source_id, source_url=urls[event.source_id],
        ))

    unique: dict[tuple[str, str, str | None, str, str], PublicActionEvidence] = {}
    for item in evidence:
        key = (item.category, item.kind, item.date, item.label, item.source_id)
        unique[key] = item
    supported = set(item.category for item in unique.values())

    stages = [
        {
            "code": code, "label": label,
            "coverage": "metadata_only" if code in supported else "unverified",
            "evidence_count": sum(1 for item in unique.values() if item.category == code),
            "normative_text_verified": False,
        }
        for code, label in STAGES
    ]
    return {
        "dossier_id": dossier.id,
        "title": dossier.title,
        "stages": stages,
        "evidence": [item.as_dict() for item in sorted(
            unique.values(), key=lambda x: (x.date or "", x.category, x.label)
        )],
        "budget_links_verified": False,
        "evaluation_links_verified": False,
        "applicable_law_verified": False,
        "limitations": [
            "La présence d'une notice ou d'un événement parlementaire ne prouve pas "
            "le contenu du droit applicable.",
            "Aucun financement, budget exécuté ou résultat n'est imputé à cette mesure "
            "sans lien documentaire explicite et vérifié.",
        ],
    }
