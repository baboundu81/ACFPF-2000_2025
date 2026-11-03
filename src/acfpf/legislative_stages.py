# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


STAGE_LABELS = {
    "deposit": "Dépôt",
    "committee": "Commission",
    "plenary": "Séance / lecture",
    "shuttle": "Navette parlementaire",
    "cmp": "Commission mixte paritaire",
    "congress": "Congrès du Parlement",
    "constitutional_review": "Contrôle constitutionnel",
    "adopted": "Adopté",
    "promulgated": "Promulgué",
    "closed": "Clos",
    "unknown": "Étape à vérifier",
}


@dataclass(frozen=True)
class LegislativeStage:
    code: str
    label: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "label": self.label}


def _normalize(value: str | None) -> str:
    decomposed = unicodedata.normalize("NFKD", value or "")
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", ascii_text.lower()).strip()


def stage(code: str) -> LegislativeStage:
    return LegislativeStage(code=code, label=STAGE_LABELS[code])


def classify_assembly_stage(label: str | None, code: str | None = None) -> LegislativeStage:
    """Map an Assemblée event to a coarse stage without guessing unknown labels."""
    text = _normalize(label)
    event_code = _normalize(code)

    if any(token in text for token in ("promulg", "journal officiel")) or event_code in {
        "prom",
        "promulgation",
    }:
        return stage("promulgated")
    if "commission mixte paritaire" in text or event_code == "cmp":
        return stage("cmp")
    if any(token in text for token in ("conseil constitutionnel", "constitutionnalite")):
        return stage("constitutional_review")
    if "congres" in text:
        return stage("congress")
    if any(
        token in text
        for token in ("adoption definitive", "adopte definitivement", "texte definitif")
    ):
        return stage("adopted")
    if any(token in text for token in ("retrait", "retire", "rejet definitif", "caduc")):
        return stage("closed")
    if "depot" in text or event_code == "depot":
        return stage("deposit")
    if "commission" in text or event_code == "com":
        return stage("committee")
    if any(token in text for token in ("nouvelle lecture", "deuxieme lecture", "navette", "transmission")):
        return stage("shuttle")
    if any(token in text for token in ("premiere lecture", "lecture definitive", "seance", "discussion")):
        return stage("plenary")
    return stage("unknown")


def classify_senate_stage(
    state: str | None,
    *,
    promulgation_date: str | None = None,
    constitutional_date: str | None = None,
) -> LegislativeStage:
    """Map the documented DOSLEG dossier state to a stable coarse stage."""
    text = _normalize(state)

    if promulgation_date or "promulgue" in text:
        return stage("promulgated")
    if any(token in text for token in ("non conforme", "conseil constitutionnel")):
        return stage("constitutional_review")
    if constitutional_date and not text:
        return stage("constitutional_review")
    if any(token in text for token in ("caduc", "non adopte", "retire", "irrecevable")):
        return stage("closed")
    if "commission mixte paritaire" in text:
        return stage("cmp")
    if "congres du parlement" in text or text == "congres":
        return stage("congress")
    if text == "adopte" or "adoption definitive" in text:
        return stage("adopted")
    if any(token in text for token in ("nouvelle lecture", "deuxieme lecture")):
        return stage("shuttle")
    if any(token in text for token in ("premiere lecture", "lecture definitive")):
        return stage("plenary")
    if "commission" in text:
        return stage("committee")
    if "depot" in text:
        return stage("deposit")
    return stage("unknown")
