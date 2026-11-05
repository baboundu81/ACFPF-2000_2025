# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Probe official parliamentary document notices for precisely linked reports."""

import json
import os
import zipfile

import pytest

from acfpf.data.assemblee_legislation import load_assembly_dossiers


@pytest.mark.skipif(
    os.environ.get("ACFPF_LIVE_SOURCES") != "1",
    reason="Live official-source checks are opt-in",
)
def test_live_assembly_report_notice_schema(tmp_path):
    path = tmp_path / "dossiers.zip"
    dossiers = load_assembly_dossiers(cache_path=path, refresh=True)
    assert dossiers
    candidates = []
    linked = []
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.startswith("json/document/") or not name.endswith(".json"):
                continue
            obj = json.loads(archive.read(name)).get("document", {})
            if not isinstance(obj, dict):
                continue
            uid = obj.get("uid")
            code = ((obj.get("classification") or {}).get("type") or {}).get("code")
            provenance = obj.get("provenance")
            if (isinstance(uid, str) and uid.startswith("RAPP")) or code == "RAPP":
                sample = {
                    "uid": uid, "code": code, "provenance": provenance,
                    "dossierRef": obj.get("dossierRef"),
                    "title": (obj.get("titres") or {}).get("titrePrincipal"),
                    "keys": sorted(obj),
                }
                candidates.append(sample)
                if obj.get("dossierRef"):
                    linked.append(sample)
    print("LIVE-REPORT-NOTICES:", len(candidates))
    print("LIVE-REPORT-LINKED:", len(linked))
    print("LIVE-REPORT-SAMPLES:", json.dumps(candidates[:3], ensure_ascii=False)[:6000])
    assert candidates, "No report notices in official archive"
