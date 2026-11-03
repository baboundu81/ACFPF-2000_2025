# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import requests


class AssemblyAmendmentDetailError(RuntimeError):
    """Raised when one official Assemblée amendment XML cannot be loaded or parsed."""


@dataclass(frozen=True)
class AssemblyAmendmentDetail:
    uid: str
    dispositif: str | None
    purpose: str | None
    sort_order: str | None
    source_url: str
    retrieved_at: str | None = None
    from_cache: bool = False

    def as_dict(self) -> dict[str, str | bool | None]:
        return {
            "uid": self.uid,
            "dispositif": self.dispositif,
            "purpose": self.purpose,
            "sort_order": self.sort_order,
            "source_url": self.source_url,
            "retrieved_at": self.retrieved_at,
            "from_cache": self.from_cache,
        }


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _clean_rich_text(value: str | None) -> str | None:
    if not value:
        return None
    text = html.unescape(value)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _element_text(root: ET.Element, name: str, *, rich: bool = False) -> str | None:
    for element in root.iter():
        if _local_name(element.tag) != name:
            continue
        raw = "".join(element.itertext()).strip()
        if rich:
            return _clean_rich_text(raw)
        return raw or None
    return None


def _validate_official_xml_url(url: str) -> None:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not (
        hostname == "assemblee-nationale.fr" or hostname.endswith(".assemblee-nationale.fr")
    ):
        raise AssemblyAmendmentDetailError("Amendment detail URL is not an official Assemblée URL")
    if not parsed.path.lower().endswith(".xml"):
        raise AssemblyAmendmentDetailError("Amendment detail URL is not an XML resource")


def parse_assembly_amendment_xml(
    blob: bytes,
    *,
    uid: str,
    source_url: str,
    retrieved_at: str | None = None,
    from_cache: bool = False,
) -> AssemblyAmendmentDetail:
    try:
        root = ET.fromstring(blob)
    except ET.ParseError as exc:
        raise AssemblyAmendmentDetailError("Unable to parse Assemblée amendment XML") from exc

    xml_uid = _element_text(root, "uid")
    if xml_uid and xml_uid != uid:
        raise AssemblyAmendmentDetailError("Amendment XML uid does not match requested amendment")

    return AssemblyAmendmentDetail(
        uid=uid,
        dispositif=_element_text(root, "dispositif", rich=True),
        purpose=_element_text(root, "exposeSommaire", rich=True),
        sort_order=_element_text(root, "triAmendement"),
        source_url=source_url,
        retrieved_at=retrieved_at,
        from_cache=from_cache,
    )


def fetch_assembly_amendment_xml(
    url: str,
    *,
    timeout: float = 20.0,
    session: requests.Session | None = None,
) -> bytes:
    _validate_official_xml_url(url)
    client = session or requests.Session()
    try:
        response = client.get(url, timeout=timeout)
        response.raise_for_status()
        return bytes(response.content)
    except requests.RequestException as exc:
        raise AssemblyAmendmentDetailError("Unable to retrieve Assemblée amendment XML") from exc


def load_assembly_amendment_detail(
    *,
    uid: str,
    url: str,
    cache_path: Path,
    max_cache_age_seconds: int = 60 * 60,
    refresh: bool = False,
) -> AssemblyAmendmentDetail:
    """Load one amendment XML on demand with a short cache and stale fallback."""
    _validate_official_xml_url(url)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if cache_path.exists() and not refresh:
        age = datetime.now(UTC).timestamp() - cache_path.stat().st_mtime
        if age <= max_cache_age_seconds:
            retrieved_at = datetime.fromtimestamp(cache_path.stat().st_mtime, UTC).isoformat()
            try:
                return parse_assembly_amendment_xml(
                    cache_path.read_bytes(),
                    uid=uid,
                    source_url=url,
                    retrieved_at=retrieved_at,
                    from_cache=True,
                )
            except AssemblyAmendmentDetailError:
                pass

    try:
        blob = fetch_assembly_amendment_xml(url)
        retrieved_at = datetime.now(UTC).isoformat()
        detail = parse_assembly_amendment_xml(
            blob,
            uid=uid,
            source_url=url,
            retrieved_at=retrieved_at,
            from_cache=False,
        )
        cache_path.write_bytes(blob)
        return detail
    except AssemblyAmendmentDetailError:
        if cache_path.exists():
            retrieved_at = datetime.fromtimestamp(cache_path.stat().st_mtime, UTC).isoformat()
            try:
                return parse_assembly_amendment_xml(
                    cache_path.read_bytes(),
                    uid=uid,
                    source_url=url,
                    retrieved_at=retrieved_at,
                    from_cache=True,
                )
            except AssemblyAmendmentDetailError:
                pass
        raise
