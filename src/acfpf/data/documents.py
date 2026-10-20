# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

from html.parser import HTMLParser
from typing import Any

import requests


class DocumentFetchError(RuntimeError):
    """Raised when an allow-listed official document cannot be fetched."""


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        elif tag in {"p", "li", "h1", "h2", "h3", "h4", "tr", "br", "article", "section"}:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        elif tag in {"p", "li", "h1", "h2", "h3", "h4", "tr", "article", "section"}:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(data)

    def text(self) -> str:
        lines = []
        for raw_line in "".join(self._parts).splitlines():
            line = " ".join(raw_line.split())
            if line:
                lines.append(line)
        return "\n".join(lines)


def extract_html_text(html: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(html)
    return parser.text()


def fetch_official_document_text(
    url: str,
    *,
    timeout: float = 20.0,
    session: requests.Session | None = None,
) -> str:
    client = session or requests.Session()
    headers = {"User-Agent": "ACFPF/0.2 (+https://github.com/baboundu81/ACFPF-2000_2025)"}
    try:
        response = client.get(url, timeout=timeout, headers=headers)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise DocumentFetchError(f"Unable to retrieve official document: {url}") from exc

    content_type = response.headers.get("Content-Type", "")
    if "html" not in content_type.lower() and not url.lower().endswith(('.html', '/')):
        raise DocumentFetchError(
            f"Unsupported document content type for the first corpus implementation: {content_type}"
        )

    text = extract_html_text(response.text)
    if len(text) < 100:
        raise DocumentFetchError(f"Official document returned too little usable text: {url}")
    return text


def split_document_text(text: str, *, max_chars: int = 1400) -> list[str]:
    """Split extracted text without cutting paragraphs unless a paragraph is very large."""
    paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0

    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append("\n".join(current))
                current = []
                current_size = 0
            for start in range(0, len(paragraph), max_chars):
                chunks.append(paragraph[start : start + max_chars])
            continue

        projected = current_size + len(paragraph) + (1 if current else 0)
        if current and projected > max_chars:
            chunks.append("\n".join(current))
            current = [paragraph]
            current_size = len(paragraph)
        else:
            current.append(paragraph)
            current_size = projected

    if current:
        chunks.append("\n".join(current))
    return chunks
