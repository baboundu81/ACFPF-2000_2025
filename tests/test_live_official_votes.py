# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Inspect official public-vote data before implementing dossier-level matching."""

from __future__ import annotations

import json
import os
import zipfile
from io import BytesIO

import pytest
import requests

SCRUTINS_URL = (
    "https://data.assemblee-nationale.fr/static/openData/repository/"
    "17/loi/scrutins/Scrutins.json.zip"
)


@pytest.mark.skipif(
    os.environ.get("ACFPF_LIVE_SOURCES") != "1",
    reason="Live official-source checks are opt-in",
)
def test_live_official_vote_archive_schema() -> None:
    response = requests.get(SCRUTINS_URL, timeout=40)
    response.raise_for_status()
    with zipfile.ZipFile(BytesIO(response.content)) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".json")]
        assert names
        print("LIVE-SCRUTINS-FILES:", len(names))
        print("LIVE-SCRUTINS-NAMES:", names[:4])
        sample = json.loads(archive.read(names[0]))
        scrutin = sample.get("scrutin", sample)
        print("LIVE-SCRUTIN-KEYS:", sorted(scrutin))
        print("LIVE-SCRUTIN-SAMPLE:", json.dumps(scrutin, ensure_ascii=False)[:1200])

        linked = []
        for name in names:
            record = json.loads(archive.read(name)).get("scrutin", {})
            objet = record.get("objet") or {}
            if not isinstance(objet, dict):
                continue
            if objet.get("dossierLegislatif") is not None or objet.get("referenceLegislative") is not None:
                linked.append({
                    "uid": record.get("uid"),
                    "dossier": objet.get("dossierLegislatif"),
                    "reference": objet.get("referenceLegislative"),
                })
        print("LIVE-SCRUTIN-EXPLICIT-LINKS:", len(linked))
        print("LIVE-SCRUTIN-LINK-SAMPLES:", json.dumps(linked[:5], ensure_ascii=False)[:1600])
