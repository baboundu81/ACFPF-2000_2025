# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""No fabricated text or cross-dossier leakage in the official HTML loader."""

from __future__ import annotations

import hashlib

import pytest

from acfpf.legislative_fulltext import OfficialTextError, fetch_official_text, official_text_url
from acfpf.legislative_versions import TextVersion, TextVersionCollection
from acfpf.web import create_app
from tests.test_web import FakeCofogService, FakeLegislationService, FakeMacroService

UID = "PIONANR5L17B2562"
HTML = (
    b"<html><body><header>ASSEMBLÃE NATIONALE</header>"
    b"<h1>PROPOSITION DE LOI</h1><h2>Article 1</h2><p>"
    + b"Un texte officiel de controle pour verifier le decodage et la provenance. " * 3
    + b"</p><script>THIS_SHOULD_BE_IGNORED</script></body></html>"
)


class FakeResponse:
    def __init__(self, body=HTML, status=200, content_type="text/html"):
        self.body = body
        self.status_code = status
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def iter_content(self, chunk_size):
        for index in range(0, len(self.body), chunk_size):
            yield self.body[index:index + chunk_size]


def test_official_html_url_cannot_be_redirected_to_other_hosts():
    assert official_text_url(UID).endswith(f"/{UID}.html")
    for bad in ("../../other", "https://evil.test/doc", "PRJL/xyz", "", "a" * 150):
        with pytest.raises(OfficialTextError):
            official_text_url(bad)


def test_official_html_has_verifiable_digest_and_does_not_include_script():
    calls = []

    def get(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse()

    record = fetch_official_text(UID, http_get=get)
    assert record.sha256 == hashlib.sha256(HTML).hexdigest()
    assert "Article 1" in record.text
    assert "THIS_SHOULD_BE_IGNORED" not in record.text
    assert record.as_dict()["article_structure_verified"] is False
    assert calls[0][1]["allow_redirects"] is False
    assert calls[0][1]["stream"] is True


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (FakeResponse(status=302), "HTTP 302"),
        (FakeResponse(content_type="application/pdf"), "not HTML"),
        (FakeResponse(body=b"<html><body>404 not found</body></html>"), "recognizable"),
        (FakeResponse(body=b"\xff\xff"), "decoded"),
    ],
)
def test_refuses_wrong_content_or_error_pages(response, message):
    with pytest.raises(OfficialTextError, match=message):
        fetch_official_text(UID, http_get=lambda *args, **kwargs: response)


def test_refuses_oversized_document():
    response = FakeResponse(body=b"X" * (2 * 1024 * 1024 + 1))
    with pytest.raises(OfficialTextError, match="size limit"):
        fetch_official_text(UID, http_get=lambda *args, **kwargs: response)


class VersionStub:
    def for_dossier(self, dossier, **kwargs):
        assert dossier.id == "DLR1"
        notice = TextVersion(
            uid=UID, title="Proposition de loi", kind="Proposition de loi",
            provenance="Texte déposé", stage_code="DEPOT", stage_label="Dépôt",
            stage_date="2026-03-03", publication_date="2026-03-03",
            notice_available=True, dossier_url=dossier.official_url,
        )
        return TextVersionCollection(dossier_id=dossier.id, available=True,
                                     reason=None, versions=(notice,))


def test_fulltext_endpoint_rejects_unlinked_document_without_network(monkeypatch):
    import acfpf.web.versions as routes

    calls = []
    monkeypatch.setattr(routes, "fetch_official_text",
                        lambda uid: calls.append(uid) or fetch_official_text(
                            uid, http_get=lambda *args, **kwargs: FakeResponse()
                        ))
    app = create_app(
        service=FakeMacroService(), cofog_service=FakeCofogService(),
        legislation_service=FakeLegislationService(), version_service=VersionStub(),
    )
    client = app.test_client()
    assert client.get("/api/legislation/UNKNOWN/versions/" + UID + "/text").status_code == 404
    assert client.get("/api/legislation/DLR1/versions/OTHER12345/text").status_code == 404
    assert calls == []
    response = client.get(f"/api/legislation/DLR1/versions/{UID}/text")
    assert response.status_code == 200
    data = response.get_json()
    assert data["dossier_id"] == "DLR1"
    assert data["uid"] == UID
    assert data["version"]["title"] == "Proposition de loi"
    assert calls == [UID]
