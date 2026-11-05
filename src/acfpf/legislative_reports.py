# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors
"""Official report notices joined to dossiers only by document.dossierRef."""

from __future__ import annotations

import json
import re
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from acfpf.data.assemblee_legislation import (
    ASSEMBLY_SOURCE_PAGE,
    AssemblyLegislationError,
    load_assembly_dossiers,
)
from acfpf.legislation import DEFAULT_CACHE_PATH, LegislativeDossier

_DOSSIER = re.compile(r"DLR[A-Za-z0-9_-]{5,100}\Z")
_REPORT = re.compile(r"RAPP[A-Za-z0-9_-]{7,100}\Z")


class ReportsError(RuntimeError):
    """Source or report provenance not verified."""


@dataclass(frozen=True)
class ReportReference:
    uid: str
    dossier_id: str
    title: str | None
    provenance: str | None
    publication_date: str | None
    origin: str
    dossier_url: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "uid": self.uid, "dossier_id": self.dossier_id, "title": self.title,
            "provenance": self.provenance, "publication_date": self.publication_date,
            "origin": self.origin, "dossier_url": self.dossier_url,
            "source_id": "assemblee_nationale_open_data",
            "full_text_available": False,
            "html_lookup_supported": self.uid.startswith("RAPPANR"),
        }


@dataclass(frozen=True)
class ReportCollection:
    dossier_id: str
    reports: tuple[ReportReference, ...]
    available: bool = True
    reason: str | None = None
    source_url: str = ASSEMBLY_SOURCE_PAGE

    def as_dict(self) -> dict[str, Any]:
        return {
            "available": self.available, "reason": self.reason,
            "dossier_id": self.dossier_id, "count": len(self.reports),
            "source_url": self.source_url,
            "reports": [item.as_dict() for item in self.reports],
        }


def _string(value: Any) -> str | None:
    return value.strip() or None if isinstance(value, str) else None


def _date(value: Any) -> str | None:
    value = _string(value)
    return value[:10] if value and re.match(r"\d{4}-\d{2}-\d{2}", value) else None


def _read(archive: zipfile.ZipFile, member: str) -> dict[str, Any] | None:
    try:
        info = archive.getinfo(member)
    except KeyError:
        return None
    if info.file_size > 4 * 1024 * 1024:
        raise ReportsError("Oversized official notice")
    try:
        payload = json.loads(archive.read(info).decode("utf-8-sig"))
    except (UnicodeError, RuntimeError, json.JSONDecodeError) as exc:
        raise ReportsError("Malformed official notice") from exc
    return payload if isinstance(payload, dict) else None


def parse_report_notices(blob: bytes, *, dossier_uid: str, dossier_url: str) -> ReportCollection:
    if not _DOSSIER.fullmatch(dossier_uid):
        raise ReportsError("Invalid official dossier UID")
    reports: list[ReportReference] = []
    seen: set[str] = set()
    try:
        with zipfile.ZipFile(BytesIO(blob)) as archive:
            payload = _read(archive, f"json/dossierParlementaire/{dossier_uid}.json")
            dossier = payload.get("dossierParlementaire", payload) if payload else None
            if not isinstance(dossier, dict) or dossier.get("uid") != dossier_uid:
                raise ReportsError("Official dossier UID mismatch")
            for member in archive.namelist():
                if not member.startswith("json/document/") or not member.endswith(".json"):
                    continue
                payload = _read(archive, member)
                doc = payload.get("document", payload) if payload else None
                if not isinstance(doc, dict) or doc.get("dossierRef") != dossier_uid:
                    continue
                classification = doc.get("classification") or {}
                kind = classification.get("type") if isinstance(classification, dict) else None
                if not isinstance(kind, dict) or kind.get("code") != "RAPP":
                    continue
                uid = doc.get("uid")
                if not isinstance(uid, str) or not _REPORT.fullmatch(uid) or member != f"json/document/{uid}.json":
                    raise ReportsError("Official report UID mismatch")
                if uid in seen:
                    continue
                seen.add(uid)
                titles = doc.get("titres") or {}
                lifecycle = doc.get("cycleDeVie") or {}
                chrono = lifecycle.get("chrono") if isinstance(lifecycle, dict) else None
                if not isinstance(chrono, dict):
                    chrono = {}
                reports.append(ReportReference(
                    uid=uid, dossier_id=dossier_uid,
                    title=_string(titles.get("titrePrincipal")) if isinstance(titles, dict) else None,
                    provenance=_string(doc.get("provenance")),
                    publication_date=_date(chrono.get("datePublicationWeb")) or _date(chrono.get("dateDepot")),
                    origin="Assemblée nationale" if uid.startswith("RAPPANR")
                    else "Autre provenance parlementaire (UID officiel)",
                    dossier_url=dossier_url,
                ))
    except (OSError, zipfile.BadZipFile) as exc:
        raise ReportsError("Official legislative archive unreadable") from exc
    reports.sort(key=lambda item: (item.publication_date or "", item.uid), reverse=True)
    return ReportCollection(dossier_id=dossier_uid, reports=tuple(reports))


class ReportsService:
    def __init__(self, *, cache_path: Path = DEFAULT_CACHE_PATH,
                 loader: Callable[..., Any] = load_assembly_dossiers) -> None:
        self.cache_path = cache_path
        self.loader = loader

    def for_dossier(self, dossier: LegislativeDossier, *, refresh: bool = False) -> ReportCollection:
        if not any(s.source_id == "assemblee_nationale_open_data" for s in dossier.sources) or not _DOSSIER.fullmatch(dossier.id):
            return ReportCollection(dossier_id=dossier.id, reports=(), available=False,
                                    reason="Aucun dossier Assemblée lié à cette référence.")
        try:
            self.loader(cache_path=self.cache_path, refresh=refresh)
            return parse_report_notices(self.cache_path.read_bytes(),
                                        dossier_uid=dossier.id, dossier_url=dossier.official_url)
        except (AssemblyLegislationError, OSError, ReportsError) as exc:
            raise ReportsError(str(exc)) from exc
