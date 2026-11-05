# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors
"""Conservative candidates for article headings from official HTML plain text.

These are navigation hints only, not validated legal articles.
"""

from __future__ import annotations

import re
from typing import Any

from acfpf.legislative_fulltext import OfficialText

_HEAD = re.compile(
    r"^Article\s+(?:unique|premier|1er|[1-9][0-9]{0,3})"
    r"(?:\s+(?:bis|ter|quater|quinquies|sexies|septies|octies|nonies|decies|[A-Z]))?$",
    flags=re.IGNORECASE,
)
MAX_LINES = 20000
MAX_CANDIDATES = 200


class ArticleDetectionError(ValueError):
    """The HTML plain text is too large for bounded heading detection."""


def detect_article_candidates(document: OfficialText) -> dict[str, Any]:
    lines = document.text.splitlines()
    if len(lines) > MAX_LINES:
        raise ArticleDetectionError("Document trop long pour un repérage borné.")
    candidates = []
    for line_number, line in enumerate(lines, start=1):
        heading = re.sub(r"\s+", " ", line).strip()
        if not _HEAD.fullmatch(heading):
            continue
        if len(candidates) >= MAX_CANDIDATES:
            raise ArticleDetectionError("Trop d'intitulés candidats pour un repérage fiable.")
        candidates.append({
            "ordinal": len(candidates) + 1,
            "heading": heading,
            "line_number": line_number,
            "article_verified": False,
        })
    return {
        "uid": document.uid,
        "url": document.url,
        "source_sha256": document.sha256,
        "source_retrieved_at": document.retrieved_at,
        "count": len(candidates),
        "candidates": candidates,
        "method": "full_line_article_heading_pattern",
        "article_structure_verified": False,
        "warning": (
            "Repérage expérimental des lignes ayant la forme d'un intitulé d'article. "
            "Les annexes, les exposés des motifs et les variations de mise en page peuvent "
            "produire des omissions ou des faux positifs. Une correspondance de titre "
            "ne prouve pas l'identité juridique de deux articles."
        ),
    }
