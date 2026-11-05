# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors
"""No secrets in logs, URLs or public results of the optional PISTE adapter."""

import json

import pytest

from acfpf.data.legifrance_piste import (
    PROD_API_BASE,
    PROD_TOKEN_URL,
    SANDBOX_API_BASE,
    SANDBOX_TOKEN_URL,
    LegifrancePisteClient,
    PisteError,
    exact_number_query,
)


class FakeResponse:
    def __init__(self, payload=None, *, status=200, chunks=None):
        self.status_code = status
        self.data = (
            chunks if chunks is not None
            else [json.dumps(payload if payload is not None else {}).encode()]
        )

    def iter_content(self, chunk_size):
        yield from self.data

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class FakeSession:
    def __init__(self):
        self.calls = []
        self.token = FakeResponse({"access_token": "private-bearer-value", "expires_in": 3600})
        self.search = FakeResponse({"results": [{"id": "not-validated"}]})

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.token if url.endswith("/oauth/token") else self.search


def test_exact_official_search_structure_and_date_bounds():
    body = exact_number_query("2019-290", as_of="2026-11-06")
    assert body["fond"] == "LODA_ETAT"
    assert body["recherche"]["champs"][0]["criteres"][0]["valeur"] == "2019-290"
    assert body["recherche"]["champs"][0]["criteres"][0]["typeRecherche"] == "EXACTE"
    assert body["recherche"]["filtres"][1]["valeur"] == "VIGUEUR"
    assert body["recherche"]["filtres"][0]["singleDate"] > 0
    for bad in ("2026", "2019-290/../../", "http://evil", "", "2019-290?x=y"):
        with pytest.raises(PisteError, match="Invalid law number"):
            exact_number_query(bad, as_of="2026-11-06")
    for bad in ("", "2026-13-05", "20261106", "tomorrow"):
        with pytest.raises(PisteError, match="Invalid effective date"):
            exact_number_query("2019-290", as_of=bad)


@pytest.mark.parametrize("sandbox,token_url,api_base", [
    (False, PROD_TOKEN_URL, PROD_API_BASE),
    (True, SANDBOX_TOKEN_URL, SANDBOX_API_BASE),
])
def test_creds_are_confined_to_oauth_and_result_never_claims_a_verified_law(
    sandbox, token_url, api_base,
):
    session = FakeSession()
    client = LegifrancePisteClient(
        client_id="secret-client-id", client_secret="secret-client-key",
        sandbox=sandbox, session=session,
    )
    result = client.search_law_number("2019-290", as_of="2026-11-06")
    assert result["match_verified"] is False
    assert result["legal_text_verified"] is False
    assert result["raw_response"]["results"][0]["id"] == "not-validated"
    assert len(session.calls) == 2
    auth_url, auth_args = session.calls[0]
    search_url, search_args = session.calls[1]
    assert auth_url == token_url
    assert search_url == api_base + "/search"
    assert auth_args["data"]["client_secret"] == "secret-client-key"
    assert auth_args["allow_redirects"] is False
    assert search_args["allow_redirects"] is False
    assert search_args["headers"]["Authorization"] == "Bearer private-bearer-value"
    assert "secret-client-key" not in search_url + json.dumps(search_args["json"])
    assert "private-bearer-value" not in json.dumps(result)
    client.search_law_number("2019-290", as_of="2026-11-06")
    assert len([url for url, _ in session.calls if url == token_url]) == 1


def test_refuses_missing_credentials_and_bad_auth_or_search():
    with pytest.raises(PisteError, match="credentials"):
        LegifrancePisteClient(client_id="", client_secret="redacted")
    session = FakeSession()
    session.token = FakeResponse(status=401)
    client = LegifrancePisteClient(client_id="id", client_secret="pw", session=session)
    with pytest.raises(PisteError, match="HTTP 401"):
        client.search_law_number("2019-290", as_of="2026-11-06")
    session.token = FakeResponse({"access_token": "token", "expires_in": 3600})
    session.search = FakeResponse(status=403)
    with pytest.raises(PisteError, match="HTTP 403"):
        client.search_law_number("2019-290", as_of="2026-11-06")


def test_rejects_overlarge_or_unrecognized_search_response():
    session = FakeSession()
    session.search = FakeResponse(chunks=[b"X" * (2 * 1024 * 1024 + 1)])
    client = LegifrancePisteClient(client_id="id", client_secret="pw", session=session)
    with pytest.raises(PisteError, match="size limit"):
        client.search_law_number("2019-290", as_of="2026-11-06")
