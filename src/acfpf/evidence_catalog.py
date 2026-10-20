# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

from pathlib import Path

import yaml

from acfpf.evidence import EvidenceRef


def load_evidence_documents(
    path: str | Path = "config/evidence_documents.yml",
) -> list[EvidenceRef]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)

    documents: list[EvidenceRef] = []
    for item in payload.get("documents", []):
        documents.append(
            EvidenceRef(
                id=item["id"],
                source_id=item["source_id"],
                stage=item["stage"],
                kind=item["kind"],
                title=item["title"],
                source_url=item["source_url"],
                date=str(item["date"]) if item.get("date") is not None else None,
                scope=item.get("scope"),
                document_id=item.get("document_id"),
                license=item.get("license"),
                metadata={"status": item.get("status", "catalogued")},
            )
        )
    return documents
