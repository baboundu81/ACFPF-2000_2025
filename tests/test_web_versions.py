# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from acfpf.legislative_versions import TextVersion, TextVersionCollection
from acfpf.web import create_app
from tests.test_web import FakeAnswerService, FakeCofogService, FakeMacroService
from tests.test_web_amendments import FakeLegislationService


class FakeVersions:
    def for_dossier(self, dossier, *, refresh=False):
        assert dossier.id == "DLR5L17N54629"
        return TextVersionCollection(
            dossier.id, True, None,
            tuple(TextVersion(
                uid=f"PRJLANR5L17B{n}", title=f"Texte officiel {n}",
                kind="Projet de loi", provenance="Texte Déposé",
                stage_code="AN1-DEPOT", stage_label="Dépôt initial",
                stage_date="2026-10-01", publication_date="2026-10-01",
                notice_available=True,
                dossier_url="https://www.assemblee-nationale.fr/dyn/17/dossiers/PLF_2027"
            ) for n in ("3210", "3211", "3212"))
        )


def make_app(*, found=True, version_service=None):
    return create_app(
        FakeMacroService(), FakeAnswerService(),
        cofog_service=FakeCofogService(),
        legislation_service=FakeLegislationService(found=found),
        version_service=version_service or FakeVersions(),
    )


def test_api_paginates_notice_references_and_does_not_claim_full_text():
    response = make_app().test_client().get(
        "/api/legislation/DLR5L17N54629/versions?offset=1&limit=1"
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 3
    assert payload["versions"][0]["uid"] == "PRJLANR5L17B3211"
    assert payload["versions"][0]["full_text_available"] is False
    assert "official_url" not in payload["versions"][0]


def test_api_validates_pagination_and_unknown_dossier():
    client = make_app().test_client()
    assert client.get("/api/legislation/DLR5L17N54629/versions?limit=200").status_code == 400
    assert make_app(found=False).test_client().get(
        "/api/legislation/DLR5L17N99999/versions"
    ).status_code == 404


def test_ui_uses_lazy_loading_and_serves_version_script():
    class FailIfFetched:
        def for_dossier(self, *_args, **_kwargs):
            raise AssertionError("Versions must not load during HTML rendering")

    client = make_app(version_service=FailIfFetched()).test_client()
    response = client.get("/textes/DLR5L17N54629")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'data-versions-dossier-id="DLR5L17N54629"' in html
    assert 'src="/static/js/versions.js"' in html
    assert "ne constituent pas le texte intégral" in html
    assert client.get("/static/js/versions.js").status_code == 200
