# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors
"""Diff is evidence-linked and must fail closed for unverified versions."""

import pytest

from acfpf.legislative_fulltext import OfficialText
from acfpf.legislative_text_diff import (
    TextComparisonError,
    compare_official_texts,
)
from acfpf.legislative_versions import TextVersion, TextVersionCollection
from acfpf.web import create_app
from tests.test_web import FakeCofogService, FakeLegislationService, FakeMacroService

A = "PIONANR5L17B1111"
B = "PIONANR5L17B2222"


def official(uid, text):
    return OfficialText(
        uid=uid,
        url=f"https://www.assemblee-nationale.fr/dyn/opendata/{uid}.html",
        text=text, sha256="a" * 64, retrieved_at="2026-11-06T00:00:00+00:00",
    )


def test_diff_keeps_source_digests_and_marks_unverified_article_alignment():
    result = compare_official_texts(
        official(A, "Assemblée nationale\nArticle 1\nDisposition initiale"),
        official(B, "Assemblée nationale\nArticle 1\nDisposition révisée"),
    )
    assert "-Disposition initiale" in result["diff"]
    assert "+Disposition révisée" in result["diff"]
    assert result["before"]["sha256"] == "a" * 64
    assert result["after"]["url"].endswith(f"/{B}.html")
    assert result["article_alignment_verified"] is False
    assert result["legal_equivalence_verified"] is False


def test_identical_text_and_reversed_identifiers_are_unambiguous():
    before = official(A, "Article 1\nBonjour")
    after = official(B, "Article 1\nBonjour")
    assert compare_official_texts(before, after)["changed"] is False
    with pytest.raises(TextComparisonError, match="distinctes"):
        compare_official_texts(before, official(A, "Texte changé"))


def test_rejects_oversized_inputs_instead_of_truncating_a_legal_diff():
    with pytest.raises(TextComparisonError, match="trop long"):
        compare_official_texts(official(A, "A" * 180_001), official(B, "B"))
    with pytest.raises(TextComparisonError, match="Trop de lignes"):
        compare_official_texts(official(A, "A\n" * 1201), official(B, "B"))


class StubVersions:
    def for_dossier(self, dossier):
        assert dossier.id == "DLR1"
        entries = tuple(
            TextVersion(
                uid=uid, title=f"Version {uid}", kind="Proposition de loi",
                provenance="Texte", stage_code="AN1", stage_label="Lecture",
                stage_date=None, publication_date=None,
                notice_available=True, dossier_url=dossier.official_url,
            )
            for uid in (A, B)
        )
        return TextVersionCollection(dossier_id=dossier.id,
                                     available=True, reason=None, versions=entries)


def test_api_fails_without_verified_both_notices_and_never_fetches_foreign_uid(monkeypatch):
    import acfpf.web.versions as routes

    fetched = []
    def loader(uid):
        fetched.append(uid)
        return official(uid, "Assemblée nationale\nArticle 1\n" + uid)

    monkeypatch.setattr(routes, "fetch_official_text", loader)
    app = create_app(
        service=FakeMacroService(), cofog_service=FakeCofogService(),
        legislation_service=FakeLegislationService(), version_service=StubVersions(),
    )
    client = app.test_client()
    base = "/api/legislation/DLR1/versions/compare"
    assert client.get(base + f"?before={A}&after={A}").status_code == 400
    assert client.get(base + f"?before={A}&after=UNLINKED123").status_code == 404
    assert client.get("/api/legislation/UNKNOWN/versions/compare" + f"?before={A}&after={B}").status_code == 404
    assert fetched == []
    response = client.get(base + f"?before={A}&after={B}")
    assert response.status_code == 200
    assert fetched == [A, B]
    result = response.get_json()
    assert result["dossier_id"] == "DLR1"
    assert result["before"]["version"]["uid"] == A
    assert result["after"]["version"]["uid"] == B
