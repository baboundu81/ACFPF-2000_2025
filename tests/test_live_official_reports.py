# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Probe official parliamentary document notices for precisely linked reports."""

import json
import os
import zipfile

import pytest

from acfpf.data.assemblee_legislation import load_assembly_dossiers
from acfpf.legislative_fulltext import fetch_official_text
from acfpf.legislative_reports import parse_report_notices


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

    target = next((item for item in dossiers if item.uid == "DLR5L17N51161"), None)
    assert target is not None, "Official control dossier missing"
    collection = parse_report_notices(
        path.read_bytes(), dossier_uid=target.uid, dossier_url=target.official_url,
    )
    assert any(item.uid == "RAPPANR5L17B0912" for item in collection.reports)
    assert all(item.dossier_id == target.uid for item in collection.reports)
    document = fetch_official_text("RAPPANR5L17B0912")
    assert document.uid == "RAPPANR5L17B0912"
    assert "ASSEMBLÉE NATIONALE" in document.text.upper()
    assert "RAPPORT" in document.text.upper()
    print("LIVE-REPORT-DOSSIER-COUNT:", len(collection.reports))

