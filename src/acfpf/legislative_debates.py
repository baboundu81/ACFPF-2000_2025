# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors
"""Conservative references to parliamentary readings, not transcripts or speeches."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from acfpf.legislation import LegislativeDossier
from acfpf.legislative_stages import classify_assembly_stage

ASSEMBLY_DEBATES_PORTAL = "https://www.assemblee-nationale.fr/dyn/17/comptes-rendus/seance"
ASSEMBLY_DEBATES_DATA = "https://data.assemblee-nationale.fr/travaux-parlementaires/debats"


@dataclass(frozen=True)
class DebateReference:
    dossier_id: str
    date: str | None
    stage_label: str
    stage_code: str | None
    source_id: str
    chamber: str | None
    search_portal: str
    transcript_verified: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "dossier_id": self.dossier_id,
            "date": self.date,
            "stage_label": self.stage_label,
            "stage_code": self.stage_code,
            "source_id": self.source_id,
            "chamber": self.chamber,
            "search_portal": self.search_portal,
            "transcript_verified": self.transcript_verified,
            "linkage": "Etape officielle du dossier, pas un compte rendu de séance identifié",
        }


def debate_references(dossier: LegislativeDossier) -> dict[str, Any]:
    """Collect official plenary-stage events without inventing a debate identifier.

    Senate-origin timeline events deliberately excluded: the link target is the
    Assembly's debate portal. Neither reading nor stage implies a speech exists.
    """
    seen: set[tuple[str | None, str | None, str, str | None]] = set()
    references: list[DebateReference] = []
    for event in dossier.events:
        if event.source_id != "assemblee_nationale_open_data":
            continue
        if event.chamber not in {None, "Assemblée nationale"}:
            continue
        stage = classify_assembly_stage(event.label, event.code)
        if stage.code != "plenary":
            continue
        key = (event.date, event.code, event.label, event.chamber)
        if key in seen:
            continue
        seen.add(key)
        references.append(DebateReference(
            dossier_id=dossier.id,
            date=event.date,
            stage_label=event.label,
            stage_code=event.code,
            source_id=event.source_id,
            chamber=event.chamber,
            search_portal=ASSEMBLY_DEBATES_PORTAL,
        ))
    references.sort(key=lambda item: (item.date or "", item.stage_label, item.stage_code or ""))
    return {
        "dossier_id": dossier.id,
        "count": len(references),
        "references": [item.as_dict() for item in references],
        "source_url": ASSEMBLY_DEBATES_DATA,
        "transcripts_available": False,
        "limitation": (
            "Ces étapes ne prouvent ni la tenue d'un débat particulier ni l'identité "
            "d'un orateur. Aucun compte rendu n'est rattaché automatiquement."
        ),
    }
