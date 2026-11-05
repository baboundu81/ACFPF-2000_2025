# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors
"""Bounded mechanical comparison of two independently retrieved official HTML texts.

No legal article matching or conclusion about which wording is applicable.
"""

from __future__ import annotations

from difflib import unified_diff
from typing import Any

from acfpf.legislative_fulltext import OfficialText

MAX_INPUT_CHARS = 180_000
MAX_LINES_PER_VERSION = 1200
MAX_DIFF_CHARS = 120_000


class TextComparisonError(ValueError):
    """Official texts cannot safely be compared by a bounded mechanical diff."""


def compare_official_texts(before: OfficialText, after: OfficialText) -> dict[str, Any]:
    if before.uid == after.uid:
        raise TextComparisonError("Deux versions distinctes sont nécessaires.")
    if (
        len(before.text) > MAX_INPUT_CHARS
        or len(after.text) > MAX_INPUT_CHARS
    ):
        raise TextComparisonError("Document trop long pour une comparaison bornée.")
    old_lines = before.text.splitlines()
    new_lines = after.text.splitlines()
    if max(len(old_lines), len(new_lines)) > MAX_LINES_PER_VERSION:
        raise TextComparisonError("Trop de lignes pour une comparaison textuelle bornée.")
    if not old_lines or not new_lines:
        raise TextComparisonError("Contenu officiel vide.")
    patch = "".join(unified_diff(
        [line + "\n" for line in old_lines],
        [line + "\n" for line in new_lines],
        fromfile=before.uid,
        tofile=after.uid,
        lineterm="\n",
        n=2,
    ))
    if len(patch) > MAX_DIFF_CHARS:
        raise TextComparisonError("Écart textuel trop volumineux pour être affiché.")
    return {
        "before": {
            "uid": before.uid, "url": before.url,
            "sha256": before.sha256, "retrieved_at": before.retrieved_at,
        },
        "after": {
            "uid": after.uid, "url": after.url,
            "sha256": after.sha256, "retrieved_at": after.retrieved_at,
        },
        "diff": patch,
        "changed": bool(patch),
        "method": "unified_diff_lines_html_plaintext",
        "article_alignment_verified": False,
        "legal_equivalence_verified": False,
        "warning": (
            "Comparaison mécanique de deux transcriptions HTML. "
            "Les suppressions ou ajouts apparents peuvent provenir de la mise en page ; "
            "ce résultat ne certifie ni la structure des articles ni le droit applicable."
        ),
    }
