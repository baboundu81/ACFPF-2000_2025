# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Official document notices associated with stages of an Assemblée dossier.

A document notice is *not* the full text of the law. Article comparisons require
separate retrieval and verification of the corresponding text content.
"""

from __future__ import annotations

import json
import re
import zipfile
from collections.abc import Callable, Iterator
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

_DOCUMENT_UID = re.compile(r"^[A-Za-z0-9_-]{8,100}$")


class TextVersionsError(RuntimeError):
    """Official archive or document notice is unavailable or unreadable."""


@dataclass(frozen=True)
class TextVersion:
    uid: str
    title: str | None
    kind: str | None
    provenance: str | None
    stage_code: str | None
    stage_label: str | None
    stage_date: str | None
    publication_date: str | None
    notice_available: bool
    dossier_url: str
    source_id: str = "assemblee_nationale_open_data"

    def as_dict(self) -> dict[str, Any]:
        return {
            "uid": self.uid,
            "title": self.title,
            "kind": self.kind,
            "provenance": self.provenance,
            "stage_code": self.stage_code,
            "stage_label": self.stage_label,
            "stage_date": self.stage_date,
            "publication_date": self.publication_date,
            "notice_available": self.notice_available,
            "dossier_url": self.dossier_url,
            "source_id": self.source_id,
            "full_text_available": False,
        }


@dataclass(frozen=True)
class TextVersionCollection:
    dossier_id: str
    available: bool
    reason: str | None
    versions: tuple[TextVersion, ...]
    source_url: str = ASSEMBLY_SOURCE_PAGE

    def as_dict(self) -> dict[str, Any]:
        return {
            "dossier_id": self.dossier_id,
            "available": self.available,
            "reason": self.reason,
            "count": len(self.versions),
            "source_url": self.source_url,
            "versions": [version.as_dict() for version in self.versions],
        }


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    return None


def _date(value: Any) -> str | None:
    text = _text(value)
    if text:
        match = re.match(r"\d{4}-\d{2}-\d{2}", text)
        if match:
            return match.group(0)
    return None


def _description(value: Any) -> str | None:
    if isinstance(value, str):
        return _text(value)
    if isinstance(value, dict):
        return _text(value.get("libelleCourt")) or _text(value.get("nomCanonique"))
    return None


def _document_uids(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        if _DOCUMENT_UID.fullmatch(value):
            yield value
    elif isinstance(value, list):
        for item in value:
            yield from _document_uids(item)
    elif isinstance(value, dict):
        if isinstance(value.get("uid"), str):
            yield from _document_uids(value["uid"])
        for name, item in value.items():
            if name in {"texte", "texteAssocie", "documentRef", "document"}:
                yield from _document_uids(item)


def _act_text_references(value: Any) -> Iterator[tuple[str, str | None, str | None, str | None]]:
    if isinstance(value, list):
        for item in value:
            yield from _act_text_references(item)
    elif isinstance(value, dict):
        if "codeActe" in value:
            code = _text(value.get("codeActe"))
            label = _description(value.get("libelleActe"))
            date = _date(value.get("dateActe"))
            for uid in _document_uids(value.get("texteAssocie")):
                yield uid, code, label, date
        for nested in value.values():
            if isinstance(nested, (dict, list)):
                yield from _act_text_references(nested)


def _json_member(archive: zipfile.ZipFile, member: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(archive.read(member).decode("utf-8-sig"))
    except KeyError:
        return None
    except (UnicodeError, json.JSONDecodeError, RuntimeError) as exc:
        raise TextVersionsError(f"Invalid official JSON archive member: {member}") from exc
    return payload if isinstance(payload, dict) else None


def parse_assembly_text_versions(
    archive_blob: bytes,
    *,
    dossier_uid: str,
    dossier_url: str,
) -> TextVersionCollection:
    """Read only the relevant dossier and its linked document notices from the official ZIP."""
    if not _DOCUMENT_UID.fullmatch(dossier_uid):
        raise TextVersionsError("Invalid official dossier UID")

    try:
        with zipfile.ZipFile(BytesIO(archive_blob)) as archive:
            dossier_payload = _json_member(
                archive, f"json/dossierParlementaire/{dossier_uid}.json"
            )
            if not dossier_payload:
                raise TextVersionsError("Dossier not found in official legislative archive")
            dossier = dossier_payload.get("dossierParlementaire", dossier_payload)
            if not isinstance(dossier, dict) or dossier.get("uid") != dossier_uid:
                raise TextVersionsError("Official dossier identity mismatch")

            versions: list[TextVersion] = []
            seen: set[str] = set()
            for uid, act_code, act_label, act_date in _act_text_references(
                dossier.get("actesLegislatifs", {})
            ):
                if uid in seen:
                    continue
                seen.add(uid)
                notice_payload = _json_member(archive, f"json/document/{uid}.json")
                notice = (
                    notice_payload.get("document", notice_payload)
                    if notice_payload else None
                )
                if isinstance(notice, dict) and notice.get("uid") != uid:
                    raise TextVersionsError("Official document UID mismatch")
                chrono = (
                    (notice.get("cycleDeVie") or {}).get("chrono") or {}
                    if isinstance(notice, dict) else {}
                )
                if not isinstance(chrono, dict):
                    chrono = {}
                titres = (notice.get("titres") or {}) if isinstance(notice, dict) else {}
                classification = (
                    (notice.get("classification") or {}).get("type") or {}
                    if isinstance(notice, dict) else {}
                )
                if not isinstance(titres, dict):
                    titres = {}
                if not isinstance(classification, dict):
                    classification = {}
                versions.append(
                    TextVersion(
                        uid=uid,
                        title=_text(titres.get("titrePrincipal")),
                        kind=_text(classification.get("libelle")),
                        provenance=_text(notice.get("provenance")) if isinstance(notice, dict) else None,
                        stage_code=act_code,
                        stage_label=act_label,
                        stage_date=act_date,
                        publication_date=_date(chrono.get("datePublicationWeb"))
                        or _date(chrono.get("dateDepot")),
                        notice_available=notice is not None,
                        dossier_url=dossier_url,
                    )
                )
    except (zipfile.BadZipFile, OSError) as exc:
        raise TextVersionsError("Unreadable official legislative archive") from exc

    versions.sort(key=lambda item: (item.stage_date or item.publication_date or "", item.uid))
    return TextVersionCollection(
        dossier_id=dossier_uid, available=True, reason=None, versions=tuple(versions)
    )


class TextVersionService:
    def __init__(
        self,
        *,
        cache_path: Path = DEFAULT_CACHE_PATH,
        loader: Callable[..., Any] = load_assembly_dossiers,
    ) -> None:
        self.cache_path = cache_path
        self.loader = loader

    def for_dossier(
        self, dossier: LegislativeDossier, *, refresh: bool = False
    ) -> TextVersionCollection:
        assembly = any(
            source.source_id == "assemblee_nationale_open_data"
            for source in dossier.sources
        )
        if not assembly or not _DOCUMENT_UID.fullmatch(dossier.id):
            return TextVersionCollection(
                dossier_id=dossier.id,
                available=False,
                reason="Aucun dossier Assemblée nationale n'est relié à cette référence.",
                versions=(),
            )
        try:
            self.loader(cache_path=self.cache_path, refresh=refresh)
            return parse_assembly_text_versions(
                self.cache_path.read_bytes(),
                dossier_uid=dossier.id,
                dossier_url=dossier.official_url,
            )
        except (AssemblyLegislationError, OSError, TextVersionsError) as exc:
            raise TextVersionsError(str(exc)) from exc
