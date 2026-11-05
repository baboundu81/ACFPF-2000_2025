# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors
"""Optional Légifrance PISTE transport, without assuming search results are verified.

PISTE subscription and client credentials are required for real requests.
No returned candidate is considered a verified legal text by this module.
"""

from __future__ import annotations

import json
import re
import time
from datetime import UTC, date, datetime, time as day_time
from typing import Any

import requests

PROD_TOKEN_URL = "https://oauth.piste.gouv.fr/api/oauth/token"
PROD_API_BASE = "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app"
SANDBOX_TOKEN_URL = "https://sandbox-oauth.piste.gouv.fr/api/oauth/token"
SANDBOX_API_BASE = "https://sandbox-api.piste.gouv.fr/dila/legifrance/lf-engine-app"
SOURCE_URL = "https://www.legifrance.gouv.fr/contenu/pied-de-page/foire-aux-questions-api"
_NUMBER = re.compile(r"\d{4}-\d{1,6}\Z")
MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class PisteError(RuntimeError):
    """PISTE unavailable or a response cannot be securely interpreted."""


def _body(response: requests.Response, *, max_bytes: int = MAX_RESPONSE_BYTES) -> Any:
    length = 0
    data = []
    for chunk in response.iter_content(chunk_size=65536):
        length += len(chunk)
        if length > max_bytes:
            raise PisteError("PISTE response exceeds configured size limit")
        data.append(chunk)
    try:
        return json.loads(b"".join(data).decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PisteError("PISTE returned invalid JSON") from exc


def exact_number_query(number: str, *, as_of: str) -> dict[str, Any]:
    """Official FAQ: LODA_ETAT, exact NUM, current-on-date status; no fuzzy search."""
    if not isinstance(number, str) or not _NUMBER.fullmatch(number):
        raise PisteError("Invalid law number")
    try:
        lookup_day = date.fromisoformat(as_of)
        if lookup_day.isoformat() != as_of:
            raise ValueError("Non-canonical date")
    except (TypeError, ValueError) as exc:
        raise PisteError("Invalid effective date") from exc
    milliseconds = int(
        datetime.combine(lookup_day, day_time(hour=12), tzinfo=UTC).timestamp() * 1000
    )
    return {
        "fond": "LODA_ETAT",
        "recherche": {
            "champs": [{
                "typeChamp": "NUM",
                "criteres": [{
                    "typeRecherche": "EXACTE", "valeur": number, "operateur": "ET",
                }],
                "operateur": "ET",
            }],
            "filtres": [
                {"facette": "DATE_VERSION", "singleDate": milliseconds},
                {"facette": "TEXT_LEGAL_STATUS", "valeur": "VIGUEUR"},
            ],
            "pageNumber": 1, "pageSize": 10,
            "operateur": "ET", "sort": "PERTINENCE",
            "typePagination": "DEFAUT",
        },
    }


class LegifrancePisteClient:
    def __init__(
        self, *, client_id: str, client_secret: str, sandbox: bool = False,
        session: requests.Session | None = None,
    ) -> None:
        if not client_id or not client_secret:
            raise PisteError("PISTE client credentials are required")
        self._id = client_id
        self._secret = client_secret
        self._session = session or requests.Session()
        self._token_url = SANDBOX_TOKEN_URL if sandbox else PROD_TOKEN_URL
        self._api_base = SANDBOX_API_BASE if sandbox else PROD_API_BASE
        self._access_token: str | None = None
        self._expires_at = 0.0

    def _token(self) -> str:
        if self._access_token and time.monotonic() < self._expires_at:
            return self._access_token
        try:
            with self._session.post(
                self._token_url, timeout=(5, 20), allow_redirects=False,
                headers={"Accept": "application/json"},
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._id,
                    "client_secret": self._secret,
                    "scope": "openid",
                },
                stream=True,
            ) as response:
                if response.status_code != 200:
                    raise PisteError(f"PISTE authentication failed (HTTP {response.status_code})")
                payload = _body(response, max_bytes=65536)
        except requests.RequestException as exc:
            raise PisteError("Unable to reach PISTE authentication service") from exc
        if not isinstance(payload, dict):
            raise PisteError("Invalid PISTE token response")
        token = payload.get("access_token")
        expires = payload.get("expires_in")
        if not isinstance(token, str) or not token or not isinstance(expires, int):
            raise PisteError("Incomplete PISTE token response")
        if expires < 60 or expires > 86400:
            raise PisteError("PISTE token has unexpected lifetime")
        self._access_token = token
        self._expires_at = time.monotonic() + expires - 30
        return token

    def search_law_number(self, number: str, *, as_of: str) -> dict[str, Any]:
        body = exact_number_query(number, as_of=as_of)
        token = self._token()
        try:
            with self._session.post(
                self._api_base + "/search",
                timeout=(5, 30),
                allow_redirects=False,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json=body, stream=True,
            ) as response:
                if response.status_code != 200:
                    raise PisteError(f"PISTE law search failed (HTTP {response.status_code})")
                result = _body(response)
        except requests.RequestException as exc:
            raise PisteError("Unable to query Légifrance PISTE service") from exc
        if not isinstance(result, dict):
            raise PisteError("Unrecognized PISTE search response")
        return {
            "law_number_requested": number,
            "as_of": as_of,
            "source_url": SOURCE_URL,
            "query_method": "official_exact_num_loda_etat",
            "match_verified": False,
            "legal_text_verified": False,
            "raw_response": result,
        }
