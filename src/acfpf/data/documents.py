# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

from html.parser import HTMLParser


class _VisibleTextParser(HTMLParser):
    """Extract visible text without making any relevance decision."""

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
        lines: list[str] = []
        for raw_line in "".join(self._parts).splitlines():
            line = " ".join(raw_line.split())
            if line:
                lines.append(line)
        return "\n".join(lines)


def extract_html_text(html: str) -> str:
    """Return all visible HTML text in source order.

    This deliberately performs no keyword filtering, semantic ranking or paragraph selection.
    """
    parser = _VisibleTextParser()
    parser.feed(html)
    return parser.text()
