# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors
"""Exact official report notices, no fuzzy associations."""

import json
import zipfile
from io import BytesIO

import pytest

from acfpf.legislative_fulltext import OfficialText
from acfpf.legislative_reports import (
    ReportCollection,
    ReportReference,
    ReportsError,
    parse_report_notices,
)
from acfpf.web import create_app
from tests.test_web import FakeCofogService, FakeLegislationService, FakeMacroService

DOSSIER = "DLR123456"
REPORT = "RAPPANR5L17B1234"
SENATE = "RAPPSNR5S499B0016"


def notice(uid, dossier, code="RAPP"):
    return {"document": {
        "uid": uid, "dossierRef": dossier,
        "classification": {"type": {"code": code}},
        "provenance": "Commission", "titres": {"titrePrincipal": "Rapport de contrôle"},
        "cycleDeVie": {"chrono": {"datePublicationWeb": "2026-10-20T15:00:00+02:00"}},
    }}


def archive(*documents):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        bundle.writestr(
            f"json/dossierParlementaire/{DOSSIER}.json",
            json.dumps({"dossierParlementaire": {"uid": DOSSIER}}),
        )
        for doc in documents:
            uid = doc["document"]["uid"]
            bundle.writestr(f"json/document/{uid}.json", json.dumps(doc))
    return buffer.getvalue()


def test_report_notices_are_exactly_linked_and_classified():
    data = archive(
        notice(REPORT, DOSSIER),
        notice("RAPPANR5L17B9999", "DLR999999"),
        notice("PRJLANR5L17B1234", DOSSIER, code="PRJL"),
        notice(SENATE, DOSSIER),
    )
    result = parse_report_notices(data, dossier_uid=DOSSIER, dossier_url="https://official.test/dossier")
    assert [report.uid for report in result.reports] == [SENATE, REPORT]
    assert all(report.dossier_id == DOSSIER for report in result.reports)
    assert result.reports[0].as_dict()["html_lookup_supported"] is False
    assert result.reports[1].as_dict()["html_lookup_supported"] is True
    assert result.reports[1].publication_date == "2026-10-20"


def test_rejects_invalid_dossier_and_malformed_archive():
    with pytest.raises(ReportsError, match="Invalid"):
        parse_report_notices(b"invalid", dossier_uid="../evil", dossier_url="ignored")
    with pytest.raises(ReportsError, match="unreadable"):
        parse_report_notices(b"invalid", dossier_uid=DOSSIER, dossier_url="ignored")


def test_rejects_broken_report_uid_without_guessing():
    data = archive(notice("bad", DOSSIER))
    with pytest.raises(ReportsError, match="UID mismatch"):
        parse_report_notices(data, dossier_uid=DOSSIER, dossier_url="ignored")


class ReportServiceStub:
    def for_dossier(self, dossier, **kwargs):
        assert dossier.id == "DLR1"
        reports = (
            ReportReference(REPORT, "DLR1", "Rapport de commission", "Commission",
                            "2026-10-20", "Assemblée nationale", dossier.official_url),
            ReportReference(SENATE, "DLR1", "Rapport du Sénat", "Commission",
                            "2026-10-21", "Autre provenance", dossier.official_url),
        )
        return ReportCollection("DLR1", reports)


def test_report_routes_enforce_dossier_scope_and_pagination(monkeypatch):
    import acfpf.web.reports as routes

    called = []

    def fake_fetch(uid):
        called.append(uid)
        return OfficialText(
            uid=uid, url=f"https://www.assemblee-nationale.fr/dyn/opendata/{uid}.html",
            text="ASSEMBLÉE NATIONALE - Rapport officiel", sha256="f" * 64,
            retrieved_at="2026-11-05T00:00:00+00:00",
        )

    monkeypatch.setattr(routes, "fetch_official_text", fake_fetch)
    app = create_app(
        service=FakeMacroService(), cofog_service=FakeCofogService(),
        legislation_service=FakeLegislationService(), report_service=ReportServiceStub(),
    )
    client = app.test_client()
    assert client.get("/api/legislation/UNKNOWN/reports").status_code == 404
    response = client.get("/api/legislation/DLR1/reports?limit=1&offset=1")
    assert response.status_code == 200
    assert response.get_json()["reports"][0]["uid"] == SENATE
    assert client.get("/api/legislation/DLR1/reports?limit=bad").status_code == 400
    assert client.get("/api/legislation/DLR1/reports/RAPPANR5L17B9999/text").status_code == 404
    assert client.get(f"/api/legislation/DLR1/reports/{SENATE}/text").status_code == 422
    assert called == []
    verified = client.get(f"/api/legislation/DLR1/reports/{REPORT}/text")
    assert verified.status_code == 200
    assert verified.get_json()["report"]["uid"] == REPORT
    assert called == [REPORT]
