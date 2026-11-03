# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import csv
import io
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import requests

ASSEMBLY_AMENDMENTS_SOURCE_PAGE = (
    "https://data.assemblee-nationale.fr/dossierLeg/liste-amendements"
)
ASSEMBLY_AMENDMENTS_CSV_URL = (
    "https://data.assemblee-nationale.fr/static/openData/repository/{legislature}/"
    "dossiers_legislatifs_opendata/{dossier_id}/libre_office.csv"
)
ASSEMBLY_AMENDMENT_PAGE_URL = (
    "https://www.assemblee-nationale.fr/dyn/{legislature}/amendements/{uid}"
)
ASSEMBLY_AMENDMENTS_LICENSE = "Licence Ouverte / Open Licence"


class AssemblyAmendmentsError(RuntimeError):
    """Raised when an Assemblée nationale amendment index cannot be loaded."""


@dataclass(frozen=True)
class AssemblyAmendmentIndexItem:
    uid: str
    number: str
    instance: str | None
    article: str | None
    author: str | None
    fate: str | None
    xml_url: str
    official_url: str
    legislature: str
    dossier_id: str
    retrieved_at: str | None = None
    from_cache: bool = False

    def as_dict(self) -> dict[str, str | bool | None]:
        return {
            "uid": self.uid,
            "number": self.number,
            "instance": self.instance,
            "article": self.article,
            "author": self.author,
            "fate": self.fate,
            "xml_url": self.xml_url,
            "official_url": self.official_url,
            "legislature": self.legislature,
            "dossier_id": self.dossier_id,
            "retrieved_at": self.retrieved_at,
            "from_cache": self.from_cache,
        }


def _normalize_header(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", ascii_text.lower()).strip()


def _decode_csv(blob: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return blob.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise AssemblyAmendmentsError("Unable to decode Assemblée nationale amendment CSV")


def _column(fieldnames: list[str], *aliases: str, required: bool = False) -> str | None:
    normalized = {name: _normalize_header(name) for name in fieldnames}
    alias_values = tuple(_normalize_header(alias) for alias in aliases)
    for alias in alias_values:
        for name, value in normalized.items():
            if value == alias:
                return name
    for alias in alias_values:
        for name, value in normalized.items():
            if alias in value:
                return name
    if required:
        raise AssemblyAmendmentsError(
            f"Required amendment CSV column not found: {aliases[0]}. "
            f"Available columns: {fieldnames}"
        )
    return None


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped or stripped.casefold() == "non renseigné":
        return None
    return stripped


def _uid_from_xml_url(url: str) -> str:
    match = re.search(r"/([^/?#]+)\.xml(?:[?#].*)?$", url)
    if not match:
        raise AssemblyAmendmentsError(f"Unable to extract amendment uid from URL: {url}")
    return match.group(1)


def parse_assembly_amendments_csv(
    blob: bytes,
    *,
    legislature: str,
    dossier_id: str,
    retrieved_at: str | None = None,
    from_cache: bool = False,
) -> tuple[AssemblyAmendmentIndexItem, ...]:
    text = _decode_csv(blob)
    sample = text[:10000]
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=";,\t").delimiter
    except csv.Error:
        delimiter = ";" if sample.count(";") >= sample.count(",") else ","

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    fieldnames = list(reader.fieldnames or [])
    if not fieldnames:
        raise AssemblyAmendmentsError("Assemblée nationale amendment CSV has no header")

    number_col = _column(
        fieldnames,
        "Numéro de l'amendement",
        "Numero amendement",
        required=True,
    )
    instance_col = _column(fieldnames, "Instance")
    article_col = _column(fieldnames, "Désignation de l'article", "Article")
    author_col = _column(fieldnames, "Auteur")
    fate_col = _column(fieldnames, "Sort de l'amendement", "Sort")
    xml_col = _column(
        fieldnames,
        "URL Amendement format XML",
        "URL Amendement XML",
        required=True,
    )
    assert number_col is not None
    assert xml_col is not None

    items: list[AssemblyAmendmentIndexItem] = []
    seen: set[str] = set()
    for row in reader:
        number = _clean(row.get(number_col))
        xml_url = _clean(row.get(xml_col))
        if not number or not xml_url:
            continue
        uid = _uid_from_xml_url(xml_url)
        if uid in seen:
            continue
        seen.add(uid)
        items.append(
            AssemblyAmendmentIndexItem(
                uid=uid,
                number=number,
                instance=_clean(row.get(instance_col)) if instance_col else None,
                article=_clean(row.get(article_col)) if article_col else None,
                author=_clean(row.get(author_col)) if author_col else None,
                fate=_clean(row.get(fate_col)) if fate_col else None,
                xml_url=xml_url,
                official_url=ASSEMBLY_AMENDMENT_PAGE_URL.format(
                    legislature=legislature,
                    uid=uid,
                ),
                legislature=legislature,
                dossier_id=dossier_id,
                retrieved_at=retrieved_at,
                from_cache=from_cache,
            )
        )
    return tuple(items)


def amendment_csv_url(legislature: str, dossier_id: str) -> str:
    if not legislature.isdigit() or not dossier_id.isdigit():
        raise ValueError("legislature and dossier_id must be numeric")
    return ASSEMBLY_AMENDMENTS_CSV_URL.format(
        legislature=legislature,
        dossier_id=dossier_id,
    )


def fetch_assembly_amendments_csv(
    *,
    legislature: str,
    dossier_id: str,
    timeout: float = 30.0,
    session: requests.Session | None = None,
) -> bytes:
    url = amendment_csv_url(legislature, dossier_id)
    client = session or requests.Session()
    try:
        response = client.get(url, timeout=timeout)
        response.raise_for_status()
        return bytes(response.content)
    except requests.RequestException as exc:
        raise AssemblyAmendmentsError(
            f"Unable to retrieve Assemblée nationale amendment index for dossier {dossier_id}"
        ) from exc


def load_assembly_amendments(
    *,
    legislature: str,
    dossier_id: str,
    cache_path: Path,
    max_cache_age_seconds: int = 60 * 60,
    refresh: bool = False,
) -> tuple[AssemblyAmendmentIndexItem, ...]:
    """Load one dossier's amendment index with a short cache and stale fallback."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if cache_path.exists() and not refresh:
        age = datetime.now(UTC).timestamp() - cache_path.stat().st_mtime
        if age <= max_cache_age_seconds:
            retrieved_at = datetime.fromtimestamp(cache_path.stat().st_mtime, UTC).isoformat()
            try:
                return parse_assembly_amendments_csv(
                    cache_path.read_bytes(),
                    legislature=legislature,
                    dossier_id=dossier_id,
                    retrieved_at=retrieved_at,
                    from_cache=True,
                )
            except AssemblyAmendmentsError:
                pass

    try:
        blob = fetch_assembly_amendments_csv(
            legislature=legislature,
            dossier_id=dossier_id,
        )
        retrieved_at = datetime.now(UTC).isoformat()
        items = parse_assembly_amendments_csv(
            blob,
            legislature=legislature,
            dossier_id=dossier_id,
            retrieved_at=retrieved_at,
            from_cache=False,
        )
        cache_path.write_bytes(blob)
        return items
    except AssemblyAmendmentsError:
        if cache_path.exists():
            retrieved_at = datetime.fromtimestamp(cache_path.stat().st_mtime, UTC).isoformat()
            try:
                return parse_assembly_amendments_csv(
                    cache_path.read_bytes(),
                    legislature=legislature,
                    dossier_id=dossier_id,
                    retrieved_at=retrieved_at,
                    from_cache=True,
                )
            except AssemblyAmendmentsError:
                pass
        raise
