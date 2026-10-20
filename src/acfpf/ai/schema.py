# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

from typing import Any


AGENT_ACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["search", "open", "read", "answer"]},
        "query": {"type": "string"},
        "source_ids": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"},
        "url": {"type": "string"},
        "document_id": {"type": "string"},
        "unit": {"type": "integer"},
        "status": {"type": "string", "enum": ["", "answered", "insufficient"]},
        "answer": {"type": "string"},
        "citations": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "action",
        "query",
        "source_ids",
        "reason",
        "url",
        "document_id",
        "unit",
        "status",
        "answer",
        "citations",
        "limitations",
    ],
    "additionalProperties": False,
}
