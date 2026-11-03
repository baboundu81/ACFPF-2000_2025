# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import json
import re
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import requests

ASSEMBLY_DATASET_URL = (
    "https://data.assemblee-nationale.fr/static/openData/repository/17/loi/"
    "dossiers_legislatifs/Dossiers_Legislatifs.json.zip"
)
ASSEMBLY_SOURCE_PAGE = "https://data.assemblee-nationale.fr/travaux-parlementaires/dossiers-legislatifs"
ASSEMBLY_DATASET_ID = "Dossiers_Legislatifs.json.zip"
ASSEMBLY_PRODUCER = "Assemblée nationale"
ASSEMBLY_LICENSE = "Licence Ouverte / Open Licence"
ASSEMBLY_DOSSIER_BASE_URL = "https://www.assemblee-nationale.fr/dyn/{legislature}/dossiers/{slug}"


class AssemblyLegislationError(RuntimeError):
    """Raised when the Assemblée nationale legislative dataset cannot be loaded."""


@dataclass(frozen=True)
class AssemblyLegislativeEvent:
    date: str | None
    label: str
    code: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {"date": self.date, "label": self.label, "code": self.code}


@dataclass(frozen=True)
class AssemblyLegislativeDossier:
    uid: str
    legislature: str
    title: str
    procedure_code: str | None
    procedure_label: str | None
    official_url: str
    events: tuple[AssemblyLegislativeEvent, ...]
    retrieved_at: str | None = None
    from_cache: bool = False

    @property
    def last_activity(self) -> str | None:
        dates = [event.date for event in self.events if event.date]
        return max(dates) if dates else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "uid": self.uid,
            "legislature": self.legislature,
            "title": self.title,
            "procedure_code": self.procedure_code,
            "procedure_label": self.procedure_label,
            "official_url": self.official_url,
            "events": [event.as_dict() for event in self.events],
            "last_activity": self.last_activity,
            "retrieved_at": self.retrieved_at,
            "from_cache": self.from_cache,
            "dataset_id": ASSEMBLY_DATASET_ID,
            "dataset_url": ASSEMBLY_DATASET_URL,
            "producer": ASSEMBLY_PRODUCER,
            "license": ASSEMBLY_LICENSE,
        }


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, (int, float)):
        return str(value)
    return None


def _date(value: Any) -> str | None:
    raw = _text(value)
    if raw is None:
        return None
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if match:
        return match.group(0)
    match = re.search(r"(\d{2})/(\d{2})/(\d{4})", raw)
    if match:
        return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"
    if re.fullmatch(r"\d{8}", raw):
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return None


def _first_text(mapping: Any, *keys: str) -> str | None:
    if not isinstance(mapping, dict):
        return None
    for key in keys:
        value = _text(mapping.get(key))
        if value:
            return value
    return None


def _walk_events(value: Any) -> Iterable[AssemblyLegislativeEvent]:
    if isinstance(value, dict):
        label = _first_text(value, "libelleActe", "libelle", "nom", "titre")
        code = _first_text(value, "codeActe", "code")
        date = _date(value.get("dateActe")) or _date(value.get("date"))
        if label and (date or code):
            yield AssemblyLegislativeEvent(date=date, label=label, code=code)
        for child in value.values():
            yield from _walk_events(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_events(child)


def _dedupe_events(events: Iterable[AssemblyLegislativeEvent]) -> tuple[AssemblyLegislativeEvent, ...]:
    seen: set[tuple[str | None, str, str | None]] = set()
    result: list[AssemblyLegislativeEvent] = []
    for event in events:
        key = (event.date, event.label, event.code)
        if key in seen:
            continue
        seen.add(key)
        result.append(event)
    result.sort(key=lambda event: (event.date or "", event.label))
    return tuple(result)


def _unwrap_dossier(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    dossier = payload.get("dossierParlementaire")
    if isinstance(dossier, dict):
        return dossier
    if "uid" in payload and ("titreDossier" in payload or "actesLegislatifs" in payload):
        return payload
    return None


def parse_assembly_dossier(
    payload: dict[str, Any], *, retrieved_at: str | None = None, from_cache: bool = False
) -> AssemblyLegislativeDossier:
    dossier = _unwrap_dossier(payload)
    if dossier is None:
        raise AssemblyLegislationError("Unsupported Assemblée nationale dossier JSON structure")

    uid = _text(dossier.get("uid"))
    legislature = _text(dossier.get("legislature")) or "17"
    title_block = dossier.get("titreDossier")
    title = _first_text(title_block, "titre", "titreChemin") or _first_text(
        dossier, "titre", "libelle"
    )
    if not uid or not title:
        raise AssemblyLegislationError("Assemblée nationale dossier is missing uid or title")

    procedure = dossier.get("procedureParlementaire")
    procedure_code = _first_text(procedure, "code")
    procedure_label = _first_text(procedure, "libelle")

    slug = _first_text(title_block, "titreChemin")
    if slug and slug.startswith("http"):
        official_url = slug
    elif slug and slug.startswith("/"):
        official_url = f"https://www.assemblee-nationale.fr{slug}"
    elif slug:
        official_url = ASSEMBLY_DOSSIER_BASE_URL.format(legislature=legislature, slug=slug)
    else:
        official_url = f"https://www.assemblee-nationale.fr/dyn/{legislature}/dossiers"

    events = _dedupe_events(_walk_events(dossier.get("actesLegislatifs", {})))
    return AssemblyLegislativeDossier(
        uid=uid,
        legislature=legislature,
        title=title,
        procedure_code=procedure_code,
        procedure_label=procedure_label,
        official_url=official_url,
        events=events,
        retrieved_at=retrieved_at,
        from_cache=from_cache,
    )


def _iter_dossier_payloads(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        if _unwrap_dossier(value) is not None:
            yield value
            return
        for child in value.values():
            yield from _iter_dossier_payloads(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_dossier_payloads(child)


def parse_assembly_archive(
    blob: bytes, *, retrieved_at: str | None = None, from_cache: bool = False
) -> tuple[AssemblyLegislativeDossier, ...]:
    dossiers: dict[str, AssemblyLegislativeDossier] = {}
    try:
        with zipfile.ZipFile(BytesIO(blob)) as archive:
            names = [name for name in archive.namelist() if name.lower().endswith(".json")]
            for name in names:
                try:
                    payload = json.loads(archive.read(name).decode("utf-8-sig"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
                for dossier_payload in _iter_dossier_payloads(payload):
                    try:
                        dossier = parse_assembly_dossier(
                            dossier_payload, retrieved_at=retrieved_at, from_cache=from_cache
                        )
                    except AssemblyLegislationError:
                        continue
                    dossiers[dossier.uid] = dossier
    except (zipfile.BadZipFile, OSError) as exc:
        raise AssemblyLegislationError(
            "Unable to decode Assemblée nationale legislative archive"
        ) from exc

    if not dossiers:
        raise AssemblyLegislationError("Assemblée nationale archive contains no readable dossiers")
    return tuple(dossiers.values())


def fetch_assembly_archive(
    *, timeout: float = 20.0, session: requests.Session | None = None
) -> bytes:
    client = session or requests.Session()
    try:
        response = client.get(ASSEMBLY_DATASET_URL, timeout=timeout)
        response.raise_for_status()
        return bytes(response.content)
    except requests.RequestException as exc:
        raise AssemblyLegislationError(
            "Unable to retrieve Assemblée nationale legislative dataset"
        ) from exc


def load_assembly_dossiers(
    *,
    cache_path: Path,
    max_cache_age_seconds: int = 6 * 60 * 60,
    refresh: bool = False,
) -> tuple[AssemblyLegislativeDossier, ...]:
    """Load legislative dossiers with a short-lived local cache and stale fallback offline."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if cache_path.exists() and not refresh:
        age = datetime.now(UTC).timestamp() - cache_path.stat().st_mtime
        if age <= max_cache_age_seconds:
            try:
                retrieved_at = datetime.fromtimestamp(cache_path.stat().st_mtime, UTC).isoformat()
                return parse_assembly_archive(
                    cache_path.read_bytes(), retrieved_at=retrieved_at, from_cache=True
                )
            except AssemblyLegislationError:
                pass

    try:
        blob = fetch_assembly_archive()
        retrieved_at = datetime.now(UTC).isoformat()
        dossiers = parse_assembly_archive(blob, retrieved_at=retrieved_at, from_cache=False)
        cache_path.write_bytes(blob)
        return dossiers
    except AssemblyLegislationError:
        if cache_path.exists():
            try:
                retrieved_at = datetime.fromtimestamp(cache_path.stat().st_mtime, UTC).isoformat()
                return parse_assembly_archive(
                    cache_path.read_bytes(), retrieved_at=retrieved_at, from_cache=True
                )
            except AssemblyLegislationError:
                pass
        raise
