# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Resolve immutable Assembly actor IDs against the official historical directory.

No approximate name matching. Never infer the voter's party from current
mandates: group identity at the vote is carried by the ballot itself.
"""

from __future__ import annotations

import json
import re
import zipfile
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Callable, Iterable

import requests

ACTORS_SOURCE = "https://data.assemblee-nationale.fr/acteurs/historique-des-deputes"
ACTORS_ARCHIVE = (
    "https://data.assemblee-nationale.fr/static/openData/repository/"
    "17/amo/tous_acteurs_mandats_organes_xi_legislature/"
    "AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip"
)
ACTORS_CACHE = Path.home() / ".cache/acfpf/assembly_actors_historical.zip"
MAX_ARCHIVE = 45 * 1024 * 1024
MAX_ACTOR = 2 * 1024 * 1024
_ACTOR_ID = re.compile(r"PA[0-9]{1,12}\Z")


class ActorDirectoryError(RuntimeError):
    """Official directory download/parse unavailable or identity mismatch."""


def parse_actor_identity(blob: bytes, *, actor_ref: str) -> str | None:
    if not _ACTOR_ID.fullmatch(actor_ref):
        raise ActorDirectoryError("Invalid actor reference")
    try:
        payload = json.loads(blob.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ActorDirectoryError("Malformed official actor JSON") from exc
    actor = payload.get("acteur") if isinstance(payload, dict) else None
    if not isinstance(actor, dict):
        raise ActorDirectoryError("Missing official actor data")
    raw_uid = actor.get("uid")
    found_uid = raw_uid.get("#text") if isinstance(raw_uid, dict) else raw_uid
    if found_uid != actor_ref:
        raise ActorDirectoryError("Official actor UID mismatch")
    state = actor.get("etatCivil")
    ident = state.get("ident") if isinstance(state, dict) else None
    if not isinstance(ident, dict):
        return None
    first, last = ident.get("prenom"), ident.get("nom")
    if not isinstance(first, str) or not isinstance(last, str):
        return None
    first, last = first.strip(), last.strip()
    if not first or not last:
        return None
    if any(ord(ch) < 32 for ch in first + last):
        raise ActorDirectoryError("Invalid actor identity characters")
    return f"{first} {last}"


def _validate_zip(payload: bytes) -> None:
    if len(payload) > MAX_ARCHIVE:
        raise ActorDirectoryError("Official actor archive is too large")
    if not zipfile.is_zipfile(BytesIO(payload)):
        raise ActorDirectoryError("Unreadable official actor archive")


def _get_directory(
    *, cache_path: Path, refresh: bool,
    http_get: Callable = requests.get,
) -> Path:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists() and not refresh:
        age = datetime.now(UTC).timestamp() - cache_path.stat().st_mtime
        if age <= 86400:
            return cache_path
    try:
        response = http_get(
            ACTORS_ARCHIVE, timeout=(10, 120), allow_redirects=False
        )
        if response.status_code != 200:
            raise ActorDirectoryError(f"Actor directory returned HTTP {response.status_code}")
        payload = bytes(response.content)
        _validate_zip(payload)
        temporary = cache_path.with_suffix(".tmp")
        temporary.write_bytes(payload)
        temporary.replace(cache_path)
    except (OSError, requests.RequestException, ActorDirectoryError) as exc:
        if not cache_path.exists():
            raise ActorDirectoryError("Historical Assembly actor directory unavailable") from exc
        try:
            _validate_zip(cache_path.read_bytes())
        except (OSError, ActorDirectoryError) as stale_exc:
            raise ActorDirectoryError("Actor directory cache unreadable") from stale_exc
    return cache_path


def resolve_actor_names(
    actor_refs: Iterable[str], *, cache_path: Path = ACTORS_CACHE,
    refresh: bool = False, http_get: Callable = requests.get,
) -> dict[str, str | None]:
    """Resolve at most 200 exact actor references; missing actors remain unknown."""
    refs = tuple(dict.fromkeys(actor_refs))
    if len(refs) > 200 or any(
        not isinstance(item, str) or not _ACTOR_ID.fullmatch(item) for item in refs
    ):
        raise ActorDirectoryError("Invalid set of actor references")
    if not refs:
        return {}
    archive_path = _get_directory(
        cache_path=cache_path, refresh=refresh, http_get=http_get
    )
    result: dict[str, str | None] = {}
    try:
        with zipfile.ZipFile(archive_path) as archive:
            for actor_ref in refs:
                member = f"json/acteur/{actor_ref}.json"
                try:
                    info = archive.getinfo(member)
                except KeyError:
                    result[actor_ref] = None
                    continue
                if info.file_size > MAX_ACTOR:
                    raise ActorDirectoryError("Official actor entry too large")
                result[actor_ref] = parse_actor_identity(
                    archive.read(member), actor_ref=actor_ref
                )
    except (OSError, RuntimeError, zipfile.BadZipFile, UnicodeError) as exc:
        if isinstance(exc, ActorDirectoryError):
            raise
        raise ActorDirectoryError("Official actor data unreadable") from exc
    return result
