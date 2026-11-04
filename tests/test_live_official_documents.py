# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Inspect official archive structure before modelling legislative text versions."""

from __future__ import annotations

import json
import os
import zipfile

import pytest

from acfpf.data.assemblee_legislation import load_assembly_dossiers


@pytest.mark.skipif(
    os.environ.get("ACFPF_LIVE_SOURCES") != "1",
    reason="Live official-source checks are opt-in",
)
def test_live_official_dossier_document_metadata(tmp_path) -> None:
    archive_path = tmp_path / "assembly-dossiers.zip"
    dossiers = load_assembly_dossiers(cache_path=archive_path, refresh=True)
    assert dossiers

    target = next((item for item in dossiers if item.uid.endswith("N54629")), None)
    assert target is not None, "PLF 2027 dossier absent de l'archive officielle"
    assert target.events
    print("LIVE-DOSSIER-UID:", target.uid)
    print("LIVE-DOSSIER-EVENTS:", len(target.events))

    with zipfile.ZipFile(archive_path) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".json")]
        print("LIVE-ARCHIVE-COUNT:", len(names))
        print("LIVE-ARCHIVE-FIRST-NAMES:", names[:4])
        candidate = next((name for name in names if "N54629" in name), None)
        assert candidate is not None, "Impossible de retrouver le fichier JSON du dossier cible"
        payload = json.loads(archive.read(candidate))
        dossier = payload.get("dossierParlementaire", payload)
        print("LIVE-DOSSIER-KEYS:", sorted(dossier))
        acts = dossier.get("actesLegislatifs", {})
        print("LIVE-ACTS-SAMPLE:", json.dumps(acts, ensure_ascii=False)[:5000])
