# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Inspect the official historical actors archive before building a name resolver."""

import json
import os
import zipfile
from io import BytesIO

import pytest
import requests

HISTORICAL_ACTORS_URL = (
    "https://data.assemblee-nationale.fr/static/openData/repository/"
    "17/amo/tous_acteurs_mandats_organes_xi_legislature/"
    "AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip"
)


@pytest.mark.skipif(
    os.environ.get("ACFPF_LIVE_SOURCES") != "1",
    reason="Live official-source checks are opt-in",
)
def test_live_historical_actors_schema():
    response = requests.get(HISTORICAL_ACTORS_URL, timeout=(15, 90))
    response.raise_for_status()
    with zipfile.ZipFile(BytesIO(response.content)) as archive:
        names = archive.namelist()
        print("LIVE-ACTORS-COUNT:", len(names))
        print("LIVE-ACTORS-FIRST-NAMES:", names[:8])
        actor_files = [name for name in names if "acteur" in name.lower() and name.endswith(".json")]
        assert actor_files, "No individual actor JSON files in official historical archive"
        print("LIVE-ACTOR-FILES:", actor_files[:4])
        actor = json.loads(archive.read(actor_files[0]))
        print("LIVE-ACTOR-SAMPLE:", json.dumps(actor, ensure_ascii=False)[:3000])
        print("LIVE-ACTOR-SIZE:", len(response.content))
