# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Fetch the official HTML rendition of a *verified* document notice on demand.

This does not reconstruct articles or infer legislative changes. The caller must
resolve the document UID against the official dossier archive first.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import quote

import requests

MAX_HTML_BYTES = 2 * 1024 * 1024
_DOCUMENT_UID = re.compile(r"[A-Z][A-Z0-9_-]{7,99}\Z")
_OFFICIAL_PREFIX = "https://www.assemblee-nationale.fr/dyn/opendata/"


class OfficialTextError(RuntimeError):
    """HTML document unavailable, unreadable or not reliably identified."""


class _ExtractText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.omit = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self.omit += 1
        if tag in {"p", "div", "section", "article", "h1", "h2", "h3", "li", "br", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self.omit = max(0, self.omit - 1)
        if tag in {"p", "div", "section", "article", "h1", "h2", "h3", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.omit:
            self.parts.append(data)

    def text(self) -> str:
        return "\n".join(
            line for line in
            (re.sub(r"[ \t\r\f\v]+", " ", line).strip()
             for line in "".join(self.parts).splitlines())
            if line
        )


@dataclass(frozen=True)
class OfficialText:
    uid: str
    url: str
    text: str
    sha256: str
    retrieved_at: str
    format: str = "html"

    def as_dict(self) -> dict[str, Any]:
        return {
            "uid": self.uid, "url": self.url, "text": self.text,
            "sha256": self.sha256, "retrieved_at": self.retrieved_at,
            "format": self.format, "verified_source": True,
            "article_structure_verified": False,
        }


def official_text_url(uid: str) -> str:
    if not isinstance(uid, str) or not _DOCUMENT_UID.fullmatch(uid):
        raise OfficialTextError("Invalid official document UID")
    return f"{_OFFICIAL_PREFIX}{quote(uid)}.html"


def fetch_official_text(uid: str, *, http_get=requests.get) -> OfficialText:
    url = official_text_url(uid)
    try:
        with http_get(
            url, timeout=(5, 30), allow_redirects=False, stream=True
        ) as response:
            if response.status_code != 200:
                raise OfficialTextError(f"Official HTML unavailable (HTTP {response.status_code})")
            media_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            if media_type not in {"text/html", "application/xhtml+xml"}:
                raise OfficialTextError("Official response is not HTML")
            chunks = []
            size = 0
            for chunk in response.iter_content(chunk_size=65536):
                size += len(chunk)
                if size > MAX_HTML_BYTES:
                    raise OfficialTextError("Official HTML exceeds size limit")
                chunks.append(chunk)
            blob = b"".join(chunks)
    except requests.RequestException as exc:
        raise OfficialTextError("Official HTML source unavailable") from exc

    try:
        parser = _ExtractText()
        parser.feed(blob.decode("utf-8-sig"))
        body = parser.text()
    except (UnicodeError, ValueError) as exc:
        raise OfficialTextError("Official HTML could not be decoded") from exc
    # Fail closed for empty/error templates rather than presenting an error page as law.
    if len(body) < 100 or "assemblée nationale" not in body.casefold():
        raise OfficialTextError("Official HTML does not contain a recognizable document")
    return OfficialText(
        uid=uid, url=url, text=body, sha256=hashlib.sha256(blob).hexdigest(),
        retrieved_at=datetime.now(UTC).isoformat(),
    )
