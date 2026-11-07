# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import json

import pytest

from acfpf.ai.provider import AIProviderError
from acfpf.web import create_app
from tests.test_web import FakeCofogService, FakeLegislationService, FakeMacroService


class FailingAnswer:
    def ask(self, question):
        raise AIProviderError(
            "Quota fournisseur atteint. Réessayez plus tard.",
            code="rate_limited",
            http_status=429,
            retry_after=7,
        )

    def iter_ask(self, question):
        yield from ()
        self.ask(question)


@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("scoped", [False, True])
def test_provider_error_keeps_safe_code_and_retry_information(stream, scoped):
    app = create_app(
        service=FakeMacroService(),
        cofog_service=FakeCofogService(),
        legislation_service=FakeLegislationService(),
        answer_service=FailingAnswer(),
    )
    payload = {"question": "Que prévoit ce texte ?"}
    if scoped:
        payload["dossier_id"] = "DLR1"
    response = app.test_client().post("/api/ask/stream" if stream else "/api/ask", json=payload)
    error = json.loads(response.data.splitlines()[-1]) if stream else response.json
    assert error["code"] == "rate_limited" and error["retry_after"] == 7
    assert error["provider_status"] == 429
    if stream:
        assert response.headers["X-Accel-Buffering"] == "no"
        assert error["type"] == "error"
    else:
        assert response.status_code == 502


@pytest.mark.parametrize("payload", [[], "question", 1, None])
def test_non_object_json_request_is_rejected(payload):
    app = create_app(
        service=FakeMacroService(),
        cofog_service=FakeCofogService(),
        legislation_service=FakeLegislationService(),
        answer_service=FailingAnswer(),
    )
    response = app.test_client().post("/api/ask", json=payload)
    assert response.status_code == 400
    assert response.json["error"] == "invalid_request"
