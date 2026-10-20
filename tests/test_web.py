# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from acfpf.data.eurostat import parse_macro_payload
from acfpf.macro import build_dashboard
from acfpf.web import create_app
from tests.test_eurostat import sample_payload


class FakeMacroService:
    def dashboard(self, *, refresh: bool = False):
        assert isinstance(refresh, bool)
        return build_dashboard(parse_macro_payload(sample_payload()))


def test_dashboard_page_renders() -> None:
    app = create_app(FakeMacroService())
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert "Vingt-cinq ans de finances publiques" in response.get_data(as_text=True)
    assert "57.3" in response.get_data(as_text=True)
    assert "Eurostat" in response.get_data(as_text=True)


def test_macro_api_returns_same_analysis() -> None:
    app = create_app(FakeMacroService())
    client = app.test_client()

    response = client.get("/api/macro")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["dataset_code"] == "gov_10dd_edpt1"
    assert payload["series"]["expenditure"]["values"][-1] == {
        "year": 2025,
        "value": 57.3,
    }


def test_health_endpoint_does_not_load_data() -> None:
    app = create_app(FakeMacroService())
    client = app.test_client()

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
