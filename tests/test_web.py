# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from acfpf.data.eurostat import EurostatError
from acfpf.macro import build_dashboard
from acfpf.web import create_app
from tests.test_eurostat import sample_dataset


class FakeMacroService:
    def dashboard(self, *, refresh: bool = False):
        assert isinstance(refresh, bool)
        return build_dashboard(sample_dataset())


class FailingMacroService:
    def dashboard(self, *, refresh: bool = False):
        raise EurostatError("simulated source failure")


def test_dashboard_page_renders() -> None:
    app = create_app(FakeMacroService())
    client = app.test_client()

    response = client.get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Vingt-cinq ans de finances publiques" in html
    assert "57.3" in html
    assert "gov_10a_main" in html
    assert "gov_10dd_edpt1" in html


def test_macro_api_returns_same_analysis() -> None:
    app = create_app(FakeMacroService())
    client = app.test_client()

    response = client.get("/api/macro")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["dataset_code"] == "gov_10a_main + gov_10dd_edpt1"
    assert payload["series"]["expenditure"]["values"][-1] == {
        "year": 2025,
        "value": 57.3,
    }
    assert len(payload["sources"]) == 2


def test_sources_remain_available_when_data_loading_fails() -> None:
    app = create_app(FailingMacroService())
    client = app.test_client()

    response = client.get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 503
    assert 'id="sources"' in html
    assert "gov_10a_main" in html
    assert "gov_10dd_edpt1" in html


def test_error_api_includes_source_catalog() -> None:
    app = create_app(FailingMacroService())
    client = app.test_client()

    response = client.get("/api/macro")
    payload = response.get_json()

    assert response.status_code == 503
    assert payload["error"] == "simulated source failure"
    assert [source["dataset_code"] for source in payload["sources"]] == [
        "gov_10a_main",
        "gov_10dd_edpt1",
    ]


def test_health_endpoint_does_not_load_data() -> None:
    app = create_app(FakeMacroService())
    client = app.test_client()

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
