# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors
"""Conservative evidence of legislative outcomes from official Senate DOSLEG events.

Outcome metadata does not establish the legally enforceable wording of a law.
"""

from __future__ import annotations

import re
from typing import Any

from acfpf.legislation import LegislativeDossier

_LAW = re.compile(r"\d{4}-\d{1,6}\Z")


def official_outcomes(dossier: LegislativeDossier) -> dict[str, Any]:
    """Expose only explicit official events; never invent JORF or Légifrance IDs."""
    evidence: list[dict[str, Any]] = []
    seen: set[tuple[str, str | None]] = set()
    for event in dossier.events:
        if event.source_id != "senat_open_data":
            continue
        if event.code not in {"CONSTITUTIONAL_COUNCIL", "PROMULGATION"}:
            continue
        key = (event.code, event.date)
        if key in seen:
            continue
        seen.add(key)
        evidence.append({
            "kind": (
                "constitutional_review" if event.code == "CONSTITUTIONAL_COUNCIL"
                else "promulgation"
            ),
            "date": event.date,
            "official_label": event.label,
            "source_id": event.source_id,
            "source_url": next(
                (source.official_url for source in dossier.sources
                 if source.source_id == "senat_open_data"),
                dossier.official_url if dossier.source_id == "senat_open_data" else None,
            ),
        })
    evidence.sort(key=lambda value: (value["date"] or "", value["kind"]))
    has_promulgation = any(item["kind"] == "promulgation" for item in evidence)
    number = dossier.law_number if has_promulgation else None
    if number and not _LAW.fullmatch(number):
        number = None
    return {
        "dossier_id": dossier.id,
        "events": evidence,
        "law_number": number,
        "promulgation_recorded": has_promulgation,
        "legifrance_text_verified": False,
        "constitutional_decision_text_verified": False,
        "warning": (
            "Ces références sont des métadonnées officielles Sénat (DOSLEG). "
            "Elles ne contiennent ni le texte de la loi publiée au JORF, "
            "ni le texte intégral d'une décision du Conseil constitutionnel. "
            "Aucun identifiant Légifrance n'est déduit d'un numéro de loi."
        ),
    }
