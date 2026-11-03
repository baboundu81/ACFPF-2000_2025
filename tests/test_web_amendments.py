# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from acfpf.legislation_detail import Amendment, AmendmentCollection, AmendmentDetail
from acfpf.web import create_app
from tests.test_legislation_detail import assembly_dossier
from tests.test_web import FakeAnswerService, FakeCofogService, FakeMacroService


class FakeLegislationService:
    def __init__(self, *, found: bool = True) -> None:
        self.found = found

    def get(self, dossier_id: str, *, refresh: bool = False):
        assert isinstance(refresh, bool)
        if self.found and dossier_id == "DLR5L17N54629":
            return assembly_dossier()
        return None

    def warnings(self):
        return ()


def amendment(number: str, fate: str, suffix: str) -> Amendment:
    labels = {
        "adopted": "Adopté",
        "rejected": "Rejeté",
        "pending": "En attente",
    }
    raw = labels[fate]
    uid = f"AMANR5L17N{suffix}"
    return Amendment(
        id=uid,
        number=number,
        chamber="Assemblée nationale",
        instance="Séance publique",
        article="Article 12",
        author="Mme Alice Martin",
        fate=fate,
        fate_label=raw,
        fate_raw=raw,
        official_url=f"https://www.assemblee-nationale.fr/dyn/17/amendements/{uid}",
        detail_url=f"https://www.assemblee-nationale.fr/dyn/opendata/{uid}.xml",
    )


class FakeAmendmentService:
    def __init__(self) -> None:
        self.items = (
            amendment("I-42", "adopted", "000042"),
            amendment("I-43", "rejected", "000043"),
            amendment("I-44", "adopted", "000044"),
        )

    def for_dossier(self, dossier, *, refresh: bool = False):
        assert dossier.id == "DLR5L17N54629"
        assert isinstance(refresh, bool)
        return AmendmentCollection(
            dossier_id=dossier.id,
            available=True,
            reason=None,
            amendments=self.items,
            retrieved_at="2026-11-03T14:00:00+00:00",
        )

    def detail_for(self, dossier, amendment_id: str, *, refresh: bool = False):
        assert dossier.id == "DLR5L17N54629"
        assert isinstance(refresh, bool)
        item = next((value for value in self.items if value.id == amendment_id), None)
        if item is None:
            return None
        return AmendmentDetail(
            amendment=item,
            dispositif="Remplacer le taux de 15 % par le taux de 12 %.",
            purpose="Limiter la hausse proposée.",
            sort_order="000042",
            retrieved_at="2026-11-03T14:05:00+00:00",
            from_cache=False,
        )


def make_app(*, found: bool = True):
    return create_app(
        FakeMacroService(),
        FakeAnswerService(),
        cofog_service=FakeCofogService(),
        legislation_service=FakeLegislationService(found=found),
        amendment_service=FakeAmendmentService(),
    )


def test_amendments_endpoint_returns_paginated_official_index() -> None:
    client = make_app().test_client()

    response = client.get(
        "/api/legislation/DLR5L17N54629/amendments?offset=1&limit=1"
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["count"] == 3
    assert payload["filtered_count"] == 3
    assert payload["offset"] == 1
    assert payload["limit"] == 1
    assert [item["number"] for item in payload["amendments"]] == ["I-43"]


def test_amendments_endpoint_filters_by_normalized_fate_before_pagination() -> None:
    client = make_app().test_client()

    response = client.get(
        "/api/legislation/DLR5L17N54629/amendments?fate=adopted&limit=1"
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["count"] == 3
    assert payload["filtered_count"] == 2
    assert payload["fate"] == "adopted"
    assert len(payload["amendments"]) == 1
    assert payload["amendments"][0]["fate_raw"] == "Adopté"


def test_amendments_endpoint_rejects_invalid_page_size() -> None:
    client = make_app().test_client()

    response = client.get(
        "/api/legislation/DLR5L17N54629/amendments?limit=999"
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_filter"


def test_amendments_endpoint_returns_404_for_unknown_dossier() -> None:
    client = make_app(found=False).test_client()

    response = client.get("/api/legislation/DLR5L17N99999/amendments")

    assert response.status_code == 404
    assert response.get_json()["error"] == "dossier_not_found"


def test_amendment_detail_endpoint_returns_dispositif_and_purpose() -> None:
    client = make_app().test_client()

    response = client.get(
        "/api/legislation/DLR5L17N54629/amendments/AMANR5L17N000042"
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["number"] == "I-42"
    assert payload["dispositif"] == "Remplacer le taux de 15 % par le taux de 12 %."
    assert payload["purpose"] == "Limiter la hausse proposée."
    assert payload["official_url"].startswith("https://www.assemblee-nationale.fr/")


def test_amendment_detail_endpoint_returns_404_for_unknown_amendment() -> None:
    client = make_app().test_client()

    response = client.get(
        "/api/legislation/DLR5L17N54629/amendments/AMANR5L17N999999"
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "amendment_not_found"
