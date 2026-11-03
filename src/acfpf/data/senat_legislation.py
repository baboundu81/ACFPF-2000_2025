# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

SENATE_DATASET_URL = "https://data.senat.fr/data/dosleg/dossiers-legislatifs.csv"
SENATE_SOURCE_PAGE = "https://data.senat.fr/dosleg/"
SENATE_HELP_PAGE = "https://data.senat.fr/aide/liste-des-dossiers-legislatifs/"
SENATE_PRODUCER = "Sénat"
SENATE_LICENSE = "Licence Ouverte / Open Licence"


class SenateLegislationError(RuntimeError):
    """Raised when the Sénat DOSLEG extract cannot be retrieved or decoded."""


@dataclass(frozen=True)
class SenateLegislativeDossier:
    uid: str
    title: str
    type_label: str | None
    initial_date: str | None
    official_url: str
    state: str | None
    constitutional_result: str | None
    constitutional_date: str | None
    promulgation_date: str | None
    law_number: str | None
    themes: tuple[str, ...]
    retrieved_at: str | None = None
    from_cache: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "uid": self.uid,
            "title": self.title,
            "type_label": self.type_label,
            "initial_date": self.initial_date,
            "official_url": self.official_url,
            "state": self.state,
            "constitutional_result": self.constitutional_result,
            "constitutional_date": self.constitutional_date,
            "promulgation_date": self.promulgation_date,
            "law_number": self.law_number,
            "themes": list(self.themes),
            "retrieved_at": self.retrieved_at,
            "from_cache": self.from_cache,
            "dataset_url": SENATE_DATASET_URL,
            "producer": SENATE_PRODUCER,
            "license": SENATE_LICENSE,
        }


def _normalize_header(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", ascii_text.lower()).strip()


def _date(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if match:
        return match.group(0)
    match = re.search(r"(\d{2})/(\d{2})/(\d{4})", raw)
    if match:
        return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"
    return None


def _slug_from_url(url: str) -> str:
    name = Path(urlparse(url).path).name
    if name.lower().endswith(".html"):
        name = name[:-5]
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", name).strip("-").lower()
    if not slug:
        raise SenateLegislationError("Sénat dossier URL does not expose a stable identifier")
    return f"senat:{slug}"


def _field_map(fieldnames: list[str] | None) -> dict[str, str]:
    if not fieldnames:
        raise SenateLegislationError("Sénat CSV has no header")
    normalized = {_normalize_header(name): name for name in fieldnames if name}

    def find(*prefixes: str, required: bool = False) -> str:
        wanted = tuple(_normalize_header(prefix) for prefix in prefixes)
        for normalized_name, raw_name in normalized.items():
            if normalized_name.startswith(wanted):
                return raw_name
        if required:
            raise SenateLegislationError(
                f"Sénat CSV is missing required column matching {prefixes!r}"
            )
        return ""

    return {
        "title": find("titre", required=True),
        "type": find("type", required=True),
        "initial_date": find("date initiale", required=True),
        "url": find("url", required=True),
        "state": find("etat", required=True),
        "constitutional_result": find(
            "decision du conseil constitutionnel",
            "resultat de la decision du conseil constitutionnel",
        ),
        "constitutional_date": find("date de la decision du conseil constitutionnel"),
        "promulgation_date": find("date de promulgation"),
        "law_number": find("numero de la loi"),
        "themes": find("themes"),
    }


def parse_senate_csv(
    blob: bytes,
    *,
    retrieved_at: str | None = None,
    from_cache: bool = False,
) -> tuple[SenateLegislativeDossier, ...]:
    """Parse the official DOSLEG dossier extract.

    The Sénat publishes this extract as a semicolon-separated Latin-1 CSV. Column names are
    public-facing labels documented by the DOSLEG help page; matching is prefix-based so harmless
    wording additions do not break ingestion.
    """
    try:
        text = blob.decode("latin-1")
    except UnicodeDecodeError as exc:
        raise SenateLegislationError("Unable to decode Sénat DOSLEG CSV") from exc

    reader = csv.DictReader(StringIO(text), delimiter=";")
    fields = _field_map(reader.fieldnames)
    dossiers: dict[str, SenateLegislativeDossier] = {}

    for row in reader:
        title = (row.get(fields["title"]) or "").strip()
        url = (row.get(fields["url"]) or "").strip()
        if not title or not url:
            continue
        try:
            uid = _slug_from_url(url)
        except SenateLegislationError:
            continue

        def value(key: str) -> str | None:
            column = fields[key]
            if not column:
                return None
            raw = (row.get(column) or "").strip()
            return raw or None

        raw_themes = value("themes") or ""
        themes = tuple(
            dict.fromkeys(
                item.strip()
                for item in re.split(r"[|,]", raw_themes)
                if item.strip()
            )
        )
        dossiers[uid] = SenateLegislativeDossier(
            uid=uid,
            title=title,
            type_label=value("type"),
            initial_date=_date(value("initial_date")),
            official_url=url,
            state=value("state"),
            constitutional_result=value("constitutional_result"),
            constitutional_date=_date(value("constitutional_date")),
            promulgation_date=_date(value("promulgation_date")),
            law_number=value("law_number"),
            themes=themes,
            retrieved_at=retrieved_at,
            from_cache=from_cache,
        )

    if not dossiers:
        raise SenateLegislationError("Sénat DOSLEG CSV contains no readable legislative dossiers")
    return tuple(dossiers.values())


def fetch_senate_csv(
    *, timeout: float = 20.0, session: requests.Session | None = None
) -> bytes:
    client = session or requests.Session()
    try:
        response = client.get(SENATE_DATASET_URL, timeout=timeout)
        response.raise_for_status()
        return bytes(response.content)
    except requests.RequestException as exc:
        raise SenateLegislationError("Unable to retrieve Sénat DOSLEG dataset") from exc


def load_senate_dossiers(
    *,
    cache_path: Path,
    max_cache_age_seconds: int = 6 * 60 * 60,
    refresh: bool = False,
) -> tuple[SenateLegislativeDossier, ...]:
    """Load Sénat dossiers with a short-lived cache and stale fallback when offline."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if cache_path.exists() and not refresh:
        age = datetime.now(UTC).timestamp() - cache_path.stat().st_mtime
        if age <= max_cache_age_seconds:
            try:
                retrieved_at = datetime.fromtimestamp(cache_path.stat().st_mtime, UTC).isoformat()
                return parse_senate_csv(
                    cache_path.read_bytes(), retrieved_at=retrieved_at, from_cache=True
                )
            except SenateLegislationError:
                pass

    try:
        blob = fetch_senate_csv()
        retrieved_at = datetime.now(UTC).isoformat()
        dossiers = parse_senate_csv(blob, retrieved_at=retrieved_at, from_cache=False)
        cache_path.write_bytes(blob)
        return dossiers
    except SenateLegislationError:
        if cache_path.exists():
            try:
                retrieved_at = datetime.fromtimestamp(cache_path.stat().st_mtime, UTC).isoformat()
                return parse_senate_csv(
                    cache_path.read_bytes(), retrieved_at=retrieved_at, from_cache=True
                )
            except SenateLegislationError:
                pass
        raise
