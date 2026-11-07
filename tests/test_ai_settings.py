# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import io
import json
import os
import re

import pytest

from acfpf.ai.openai_compatible import OpenAICompatibleProvider
from tests.test_web import make_app

URL = "/configuration-ia"
KEY = "synthetic-test-key-not-a-real-credential"
KEY_BYTES = KEY.encode()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ACFPF_LLM_PROVIDER", "gemini")
    monkeypatch.delenv("ACFPF_LLM_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    return make_app().test_client()


def token(client):
    html = client.get(URL).get_data(as_text=True)
    return re.search(r'name="csrf_token" value="([^"]+)"', html)[1]


def activate(client, *, provider="groq", content=KEY_BYTES, csrf=None, follow=False):
    data = {
        "csrf_token": token(client) if csrf is None else csrf,
        "operation": "activate",
        "provider": provider,
    }
    if content is not None:
        data["key_file"] = (io.BytesIO(content), "never-echo-this-filename.txt")
    return client.post(URL, data=data, follow_redirects=follow)


def test_import_updates_question_and_assisted_browse_without_network_on_import(
    client,
    monkeypatch,
    caplog,
):
    calls = []

    def fake_completion(provider, request):
        calls.append((provider.name, provider.model, request.response_schema_name))
        assert provider.api_key == KEY
        assert KEY not in request.user_prompt
        if request.response_schema_name == "acfpf_legislative_query_plan":
            return {
                "query": "logement",
                "status": "active",
                "chamber": "",
                "stage": "",
                "theme": "",
                "text_type": "",
                "from_year": 0,
                "to_year": 0,
            }
        return {
            "action": "answer",
            "status": "insufficient",
            "answer": "Pas de preuve.",
            "citations": [],
            "limitations": [],
        }

    monkeypatch.setattr(OpenAICompatibleProvider, "complete_json", fake_completion)
    assert client.get("/healthz").json["ai"] == "disabled"
    assert 'href="/configuration-ia"' in client.get("/").get_data(as_text=True)
    response = activate(client, content=b"\xef\xbb\xbf" + KEY.encode() + b"\r\n", follow=True)
    assert response.history[0].status_code == 303
    assert response.headers["Cache-Control"] == "no-store"
    html = response.get_data(as_text=True)
    assert "Clé chargée" in html and "openai/gpt-oss-120b" in html
    assert KEY not in html and "never-echo-this-filename" not in html
    assert not calls  # Configuration must not consume quota or verify a credential.
    assert client.get("/healthz").json["ai"] == "enabled"
    assert 'id="ask-form"' in client.get("/").get_data(as_text=True)
    assert 'id="dossier-chat-form"' in client.get("/textes/DLR1").get_data(as_text=True)
    assert client.post("/api/ask", json={"question": "Une question"}).json["provider"] == "groq"
    result = client.post("/api/ask/stream", json={"question": "Une question", "dossier_id": "DLR1"})
    events = [json.loads(line) for line in result.data.splitlines()]
    assert events[-1]["answer"]["provider"] == "groq"
    browse = client.get("/api/legislation?q=logement&assist=1").json
    assert browse["planner_available"] and browse["results"]
    assert [call[2] for call in calls] == [None, None, "acfpf_legislative_query_plan"]
    assert all(call[:2] == ("groq", "openai/gpt-oss-120b") for call in calls)
    assert KEY not in result.get_data(as_text=True) and KEY not in caplog.text
    assert "ACFPF_LLM_API_KEY" not in os.environ
    assert make_app().test_client().get("/healthz").json["ai"] == "disabled"


@pytest.mark.parametrize(
    ("provider", "content", "status"),
    [
        ("other", b"secret", 400),
        ("groq", None, 400),
        ("groq", b"", 400),
        ("groq", b"secret\nsecond-key", 400),
        ("groq", b"secret\xff", 400),
        ("groq", b"a" * 4097, 400),
        ("groq", b"a" * 16384, 413),
    ],
)
def test_rejected_import_leaves_current_provider_untouched(client, provider, content, status):
    assert activate(client, provider="gemini").status_code == 303
    response = activate(client, provider=provider, content=content)
    assert response.status_code == status
    html = response.get_data(as_text=True)
    assert "Clé chargée" in html and "gemini-3.8-flash" in html
    assert 'role="alert"' in html and KEY not in html and "second-key" not in html


def test_reset_restores_startup_provider_and_model(monkeypatch):
    monkeypatch.setenv("ACFPF_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("ACFPF_LLM_API_KEY", "startup-synthetic-key")
    monkeypatch.setenv("ACFPF_LLM_MODEL", "startup-model")
    client = make_app().test_client()
    assert activate(client).status_code == 303
    response = client.post(
        URL, data={"operation": "reset", "csrf_token": token(client)}, follow_redirects=True
    )
    html = response.get_data(as_text=True)
    assert response.history[0].status_code == 303
    assert "startup-model" in html and "Clé chargée" not in html
    assert KEY not in html and "startup-synthetic-key" not in html


def test_csrf_guards_activation_and_reset(client):
    assert activate(client, csrf="invalid-é").status_code == 403
    assert client.get("/healthz").json["ai"] == "disabled"
    assert activate(client).status_code == 303
    assert client.post(URL, data={"operation": "reset"}).status_code == 403
    assert client.get("/healthz").json["ai"] == "enabled"
    assert (
        client.post(URL, data={"operation": "reset", "csrf_token": token(client)}).status_code
        == 303
    )
    assert client.get("/healthz").json["ai"] == "disabled"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"base_url": "http://untrusted.example"},
        {"environ_overrides": {"REMOTE_ADDR": "192.0.2.15"}},
    ],
)
def test_settings_are_unavailable_off_loopback_and_on_untrusted_host(client, kwargs):
    assert client.get(URL, **kwargs).status_code == 404
    assert client.post(URL, data={"operation": "reset"}, **kwargs).status_code == 404
    assert URL not in client.get("/", **kwargs).get_data(as_text=True)


def test_settings_can_be_disabled_on_nonlocal_listener(client):
    client.application.config["AI_SETTINGS_ENABLED"] = False
    assert client.get(URL).status_code == 404
    assert URL not in client.get("/").get_data(as_text=True)


def test_provider_change_does_not_switch_an_inflight_stream(client, monkeypatch):
    monkeypatch.setattr(
        OpenAICompatibleProvider,
        "complete_json",
        lambda _provider, _request: {
            "action": "answer",
            "status": "insufficient",
            "answer": "Pas de preuve.",
            "citations": [],
            "limitations": [],
        },
    )
    assert activate(client, provider="groq").status_code == 303
    response = client.post("/api/ask/stream", json={"question": "En cours"}, buffered=False)
    try:
        other_client = client.application.test_client()
        assert activate(other_client, provider="gemini").status_code == 303
        events = [json.loads(line) for line in response.data.splitlines()]
        assert events[-1]["answer"]["provider"] == "groq"
        assert (
            other_client.post("/api/ask", json={"question": "Suivante"}).json["provider"]
            == "gemini"
        )
    finally:
        response.close()
