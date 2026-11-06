# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors
"""Article heading candidates must never imply verified normative segmentation."""

import pytest

from acfpf.legislative_articles import (
    ArticleDetectionError,
    detect_article_candidates,
)
from acfpf.legislative_fulltext import OfficialText
from acfpf.web import create_app
from tests.test_legislative_text_diff import A, B, StubVersions
from tests.test_web import FakeCofogService, FakeLegislationService, FakeMacroService


def document(uid, text):
    return OfficialText(
        uid=uid,
        url=f"https://www.assemblee-nationale.fr/dyn/opendata/{uid}.html",
        text=text, sha256="b" * 64, retrieved_at="2026-11-06T01:00:00+00:00",
    )


def test_full_line_candidates_keep_position_without_guessing_articles():
    result = detect_article_candidates(document(
        A,
        "Assemblée nationale\nEXPOSÉ DES MOTIFS\n"
        "L'article 1er est discuté dans cet exposé.\n"
        "Article unique\nDisposition initiale\n"
        "Article 2 bis\nAutre disposition\n",
    ))
    assert result["count"] == 2
    assert [item["heading"] for item in result["candidates"]] == [
        "Article unique", "Article 2 bis",
    ]
    assert [item["line_number"] for item in result["candidates"]] == [4, 6]
    assert result["article_structure_verified"] is False
    assert all(not item["article_verified"] for item in result["candidates"])
    assert result["source_sha256"] == "b" * 64


def test_empty_document_and_limited_output_do_not_invent_articles():
    result = detect_article_candidates(document(A, "Pas de titre d'article autonome."))
    assert result["count"] == 0
    with pytest.raises(ArticleDetectionError, match="Trop d'intitulés"):
        detect_article_candidates(document(A, "Article unique\n" * 201))
    with pytest.raises(ArticleDetectionError, match="trop long"):
        detect_article_candidates(document(A, "a\n" * 20001))


def test_candidates_api_requires_a_document_notice_in_the_correct_dossier(monkeypatch):
    import acfpf.web.versions as routes

    calls = []
    def fake_fetch(uid):
        calls.append(uid)
        return document(uid, "Assemblée nationale\nArticle 1er\nDisposition")

    monkeypatch.setattr(routes, "fetch_official_text", fake_fetch)
    app = create_app(
        service=FakeMacroService(), cofog_service=FakeCofogService(),
        legislation_service=FakeLegislationService(), version_service=StubVersions(),
    )
    client = app.test_client()
    assert client.get(
        f"/api/legislation/UNKNOWN/versions/{A}/article-candidates"
    ).status_code == 404
    assert client.get(
        "/api/legislation/DLR1/versions/OTHER12345/article-candidates"
    ).status_code == 404
    assert calls == []
    response = client.get(f"/api/legislation/DLR1/versions/{B}/article-candidates")
    assert response.status_code == 200
    result = response.get_json()
    assert result["uid"] == B
    assert result["dossier_id"] == "DLR1"
    assert result["count"] == 1
    assert calls == [B]
