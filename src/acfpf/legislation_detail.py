# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from acfpf.data.assemblee_amendment_detail import (
    AssemblyAmendmentDetail,
    AssemblyAmendmentDetailError,
    load_assembly_amendment_detail,
)
from acfpf.data.assemblee_amendments import (
    ASSEMBLY_AMENDMENTS_SOURCE_PAGE,
    AssemblyAmendmentIndexItem,
    AssemblyAmendmentsError,
    load_assembly_amendments,
)
from acfpf.legislation import LegislativeDossier

DEFAULT_AMENDMENTS_CACHE_DIR = Path.home() / ".cache" / "acfpf" / "amendments"


class LegislativeDetailError(RuntimeError):
    """Raised when structured details of a legislative dossier cannot be loaded."""


@dataclass(frozen=True)
class Amendment:
    id: str
    number: str
    chamber: str
    instance: str | None
    article: str | None
    author: str | None
    fate: str
    fate_label: str
    fate_raw: str | None
    official_url: str
    detail_url: str
    source_id: str = "assemblee_nationale_open_data"

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "number": self.number,
            "chamber": self.chamber,
            "instance": self.instance,
            "article": self.article,
            "author": self.author,
            "fate": self.fate,
            "fate_label": self.fate_label,
            "fate_raw": self.fate_raw,
            "official_url": self.official_url,
            "detail_url": self.detail_url,
            "source_id": self.source_id,
        }


@dataclass(frozen=True)
class AmendmentDetail:
    amendment: Amendment
    dispositif: str | None
    purpose: str | None
    sort_order: str | None
    retrieved_at: str | None
    from_cache: bool

    def as_dict(self) -> dict[str, Any]:
        payload = self.amendment.as_dict()
        payload.update(
            {
                "dispositif": self.dispositif,
                "purpose": self.purpose,
                "sort_order": self.sort_order,
                "retrieved_at": self.retrieved_at,
                "from_cache": self.from_cache,
            }
        )
        return payload


@dataclass(frozen=True)
class AmendmentCollection:
    dossier_id: str
    available: bool
    reason: str | None
    amendments: tuple[Amendment, ...]
    source_url: str = ASSEMBLY_AMENDMENTS_SOURCE_PAGE
    retrieved_at: str | None = None
    from_cache: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "dossier_id": self.dossier_id,
            "available": self.available,
            "reason": self.reason,
            "source_url": self.source_url,
            "retrieved_at": self.retrieved_at,
            "from_cache": self.from_cache,
            "count": len(self.amendments),
            "amendments": [item.as_dict() for item in self.amendments],
        }


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", ascii_text.lower()).strip()


def normalize_amendment_fate(raw: str | None) -> tuple[str, str]:
    value = _normalize(raw or "")
    if not value or value == "non renseigne" or "en traitement" in value or "a discuter" in value:
        return "pending", "En attente"
    if "adopte" in value:
        return "adopted", "Adopté"
    if "rejete" in value:
        return "rejected", "Rejeté"
    if "retire" in value:
        return "withdrawn", "Retiré"
    if "non soutenu" in value:
        return "not_supported", "Non soutenu"
    if "tombe" in value:
        return "fallen", "Tombé"
    if "irrecevable" in value:
        return "inadmissible", "Irrecevable"
    if "discute" in value:
        return "discussed", "Discuté — sort à vérifier"
    return "unknown", "Sort à vérifier"


def assembly_numeric_dossier_id(dossier: LegislativeDossier) -> str | None:
    """Return the numeric Assemblée open-data dossier id when it is explicit in its UID."""
    if not any(source.source_id == "assemblee_nationale_open_data" for source in dossier.sources):
        return None
    match = re.search(r"N(\d+)$", dossier.id)
    return match.group(1) if match else None


def _to_domain(item: AssemblyAmendmentIndexItem) -> Amendment:
    fate, fate_label = normalize_amendment_fate(item.fate)
    return Amendment(
        id=item.uid,
        number=item.number,
        chamber="Assemblée nationale",
        instance=item.instance,
        article=item.article,
        author=item.author,
        fate=fate,
        fate_label=fate_label,
        fate_raw=item.fate,
        official_url=item.official_url,
        detail_url=item.xml_url,
    )


def _merge_detail(amendment: Amendment, detail: AssemblyAmendmentDetail) -> AmendmentDetail:
    return AmendmentDetail(
        amendment=amendment,
        dispositif=detail.dispositif,
        purpose=detail.purpose,
        sort_order=detail.sort_order,
        retrieved_at=detail.retrieved_at,
        from_cache=detail.from_cache,
    )


class AmendmentService:
    def __init__(
        self,
        *,
        cache_dir: Path = DEFAULT_AMENDMENTS_CACHE_DIR,
        loader: Callable[..., tuple[AssemblyAmendmentIndexItem, ...]] = load_assembly_amendments,
        detail_loader: Callable[..., AssemblyAmendmentDetail] = load_assembly_amendment_detail,
    ) -> None:
        self.cache_dir = cache_dir
        self.loader = loader
        self.detail_loader = detail_loader

    def for_dossier(
        self,
        dossier: LegislativeDossier,
        *,
        refresh: bool = False,
    ) -> AmendmentCollection:
        numeric_id = assembly_numeric_dossier_id(dossier)
        if numeric_id is None:
            return AmendmentCollection(
                dossier_id=dossier.id,
                available=False,
                reason=(
                    "Aucun identifiant de dossier Assemblée nationale compatible n'est disponible "
                    "pour charger l'index structuré des amendements."
                ),
                amendments=(),
            )

        legislature = dossier.legislature or "17"
        cache_path = self.cache_dir / f"assembly-{legislature}-{numeric_id}.csv"
        try:
            raw = self.loader(
                legislature=legislature,
                dossier_id=numeric_id,
                cache_path=cache_path,
                refresh=refresh,
            )
        except AssemblyAmendmentsError as exc:
            raise LegislativeDetailError(str(exc)) from exc

        amendments = tuple(_to_domain(item) for item in raw)
        retrieved_at = raw[0].retrieved_at if raw else None
        from_cache = bool(raw) and all(item.from_cache for item in raw)
        return AmendmentCollection(
            dossier_id=dossier.id,
            available=True,
            reason=None,
            amendments=amendments,
            retrieved_at=retrieved_at,
            from_cache=from_cache,
        )

    def detail_for(
        self,
        dossier: LegislativeDossier,
        amendment_id: str,
        *,
        refresh: bool = False,
    ) -> AmendmentDetail | None:
        wanted = amendment_id.strip()
        if not wanted:
            return None
        collection = self.for_dossier(dossier, refresh=refresh)
        amendment = next((item for item in collection.amendments if item.id == wanted), None)
        if amendment is None:
            return None

        cache_path = self.cache_dir / "details" / f"{amendment.id}.xml"
        try:
            detail = self.detail_loader(
                uid=amendment.id,
                url=amendment.detail_url,
                cache_path=cache_path,
                refresh=refresh,
            )
        except AssemblyAmendmentDetailError as exc:
            raise LegislativeDetailError(str(exc)) from exc
        return _merge_detail(amendment, detail)
