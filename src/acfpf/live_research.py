# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from html.parser import HTMLParser
from io import BytesIO
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from pypdf import PdfReader

from acfpf.data.documents import extract_html_text
from acfpf.source_registry import Source, load_source_map

DISCOVERY_URL = "https://html.duckduckgo.com/html/"
MAX_RESULTS = 8
MAX_HTML_BYTES = 3_000_000
MAX_PDF_BYTES = 12_000_000
MAX_DISCOVERY_BYTES = 1_000_000
MAX_PDF_PAGES = 400
MAX_EXTRACTED_CHARS = 1_000_000
STREAM_CHUNK_BYTES = 32_768
MAX_REDIRECTS = 5
HTML_CONTENT_TYPES = {"text/html", "application/xhtml+xml"}
HTML_UNIT_CHARS = 12_000
PDF_PAGES_PER_UNIT = 4
REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}


class LiveResearchError(RuntimeError):
    """Base class for live research failures."""


class SourceNotAllowed(LiveResearchError):
    """Raised when a requested URL is outside the ACFPF allow-list."""


class DocumentTooLarge(LiveResearchError):
    """Raised when a live document exceeds the safety limit."""


@dataclass(frozen=True)
class SearchResult:
    source_id: str
    title: str
    url: str

    def as_dict(self) -> dict[str, str]:
        return {"source_id": self.source_id, "title": self.title, "url": self.url}


@dataclass(frozen=True)
class DocumentUnit:
    index: int
    locator: str
    text: str


@dataclass(frozen=True)
class LiveDocument:
    document_id: str
    source_id: str
    title: str
    url: str
    retrieved_at: str
    sha256: str
    content_type: str
    units: tuple[DocumentUnit, ...]

    def metadata(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "source_id": self.source_id,
            "title": self.title,
            "url": self.url,
            "retrieved_at": self.retrieved_at,
            "sha256": self.sha256,
            "content_type": self.content_type,
            "unit_count": len(self.units),
        }


class _SearchResultParser(HTMLParser):
    """Extract result links only. Search-engine snippets are intentionally discarded."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[tuple[str, str]] = []
        self._href: str | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        values = dict(attrs)
        classes = (values.get("class") or "").split()
        href = values.get("href")
        if "result__a" in classes and href:
            self._href = href
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            title = re.sub(r"\s+", " ", "".join(self._parts)).strip()
            self.results.append((self._href, title))
            self._href = None
            self._parts = []


def _parse_search_results(html: str) -> list[tuple[str, str]]:
    parser = _SearchResultParser()
    parser.feed(html)
    return parser.results


def _redirect_target(url: str) -> str:
    parsed = urlparse(url)
    if parsed.hostname not in {"duckduckgo.com", "html.duckduckgo.com"}:
        return url
    target = parse_qs(parsed.query).get("uddg", [None])[0]
    return target if target else url


def _html_title(html: str, fallback: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return fallback
    title = re.sub(r"<[^>]+>", "", match.group(1))
    return re.sub(r"\s+", " ", unescape(title)).strip() or fallback


def _split_html_units(text: str) -> tuple[DocumentUnit, ...]:
    """Split in source order only; no lexical or semantic relevance filtering is applied."""
    if not text.strip():
        return ()
    units: list[DocumentUnit] = []
    start = 0
    index = 1
    while start < len(text):
        end = min(start + HTML_UNIT_CHARS, len(text))
        if end < len(text):
            boundary = text.rfind("\n", start, end)
            if boundary > start + HTML_UNIT_CHARS // 2:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            units.append(DocumentUnit(index=index, locator=f"segment {index}", text=chunk))
            index += 1
        start = max(end, start + 1)
    return tuple(units)


def _pdf_units(content: bytes) -> tuple[DocumentUnit, ...]:
    """Group contiguous PDF pages without ranking or dropping readable pages."""
    reader = PdfReader(BytesIO(content))
    if reader.is_encrypted:
        raise LiveResearchError("Le PDF est chiffré et ne peut pas être lu.")
    if len(reader.pages) > MAX_PDF_PAGES:
        raise DocumentTooLarge("Le PDF dépasse la limite de pages lisibles.")
    units: list[DocumentUnit] = []
    total_chars = 0
    for start in range(0, len(reader.pages), PDF_PAGES_PER_UNIT):
        end = min(start + PDF_PAGES_PER_UNIT, len(reader.pages))
        page_texts = [
            (reader.pages[index].extract_text() or "").strip() for index in range(start, end)
        ]
        text = "\n\n".join(item for item in page_texts if item)
        total_chars += len(text)
        if total_chars > MAX_EXTRACTED_CHARS:
            raise DocumentTooLarge("Le texte du PDF dépasse la limite de lecture.")
        if not text:
            continue
        first_page = start + 1
        last_page = end
        locator = (
            f"page {first_page}" if first_page == last_page else f"pages {first_page}-{last_page}"
        )
        units.append(DocumentUnit(index=len(units) + 1, locator=locator, text=text))
    return tuple(units)


class LiveOfficialResearch:
    """Discover and read live documents while enforcing ACFPF's official-source allow-list."""

    def __init__(
        self,
        *,
        sources: dict[str, Source] | None = None,
        session: requests.Session | None = None,
        timeout: float = 20.0,
    ) -> None:
        self.sources = sources if sources is not None else load_source_map()
        self.session = session or requests.Session()
        self.timeout = timeout
        self._document_counter = 0
        self._documents: dict[str, LiveDocument] = {}

    def spawn(self) -> LiveOfficialResearch:
        """Create an isolated, empty research session for one user question."""
        return LiveOfficialResearch(sources=self.sources, timeout=self.timeout)

    def source_catalog(self) -> list[dict[str, object]]:
        return [
            {
                "id": source.id,
                "name": source.name,
                "priority": source.priority,
                "themes": list(source.themes),
                "evidence_stages": list(source.evidence_stages),
                "allowed_domains": list(source.allowed_domains),
            }
            for source in self.sources.values()
            if source.live_research
        ]

    def _source_for_url(self, url: str) -> Source:
        try:
            if not isinstance(url, str) or re.search(r"[\x00-\x20\x7f\\]", url):
                raise ValueError("Invalid characters")
            parsed = urlparse(url)
            hostname = (parsed.hostname or "").lower().rstrip(".")
            port = parsed.port
        except ValueError as exc:
            raise SourceNotAllowed("L’URL officielle est invalide.") from exc
        if parsed.scheme != "https" or parsed.username or parsed.password:
            raise SourceNotAllowed("Seules les URL HTTPS sans identifiants sont autorisées.")
        if port not in {None, 443}:
            raise SourceNotAllowed("Le port de cette URL n’est pas autorisé.")
        if not hostname:
            raise SourceNotAllowed("URL has no valid hostname")
        candidates: list[Source] = []
        for source in self.sources.values():
            if not source.live_research:
                continue
            for domain in source.allowed_domains:
                allowed = domain.lower().rstrip(".")
                if hostname == allowed or hostname.endswith(f".{allowed}"):
                    candidates.append(source)
                    break
        if len(candidates) == 1:
            return candidates[0]
        # A shared parent domain (e.g. ec.europa.eu) must not mislabel Commission
        # documents as Eurostat. Prefer an exact base host/path; refuse ambiguous provenance.
        matches = []
        for source in candidates:
            base = urlparse(source.base_url)
            base_path = base.path.rstrip("/")
            if hostname == base.hostname and (
                parsed.path == base_path or parsed.path.startswith(base_path + "/")
            ):
                matches.append((len(base_path), source))
        if matches:
            longest = max(length for length, _ in matches)
            best = [source for length, source in matches if length == longest]
            if len(best) == 1:
                return best[0]
        if candidates:
            raise SourceNotAllowed("L’URL correspond à plusieurs sources : provenance ambiguë.")
        raise SourceNotAllowed(f"Le domaine n’est pas autorisé par ACFPF : {hostname}")

    def _get_official(self, url: str) -> tuple[requests.Response, Source, str]:
        """Validate every redirect before requesting it, without reading redirect bodies."""
        current_url = url
        for _ in range(MAX_REDIRECTS + 1):
            source = self._source_for_url(current_url)
            try:
                response = self.session.get(
                    current_url,
                    headers={"User-Agent": "ACFPF/0.3 live-research"},
                    timeout=self.timeout,
                    allow_redirects=False,
                    stream=True,
                )
            except requests.RequestException as exc:
                raise LiveResearchError(
                    "La source officielle est indisponible ou trop lente."
                ) from exc

            if response.status_code in REDIRECT_STATUS_CODES:
                location = response.headers.get("Location")
                response.close()
                if not location:
                    raise LiveResearchError("La source a renvoyé une redirection sans destination.")
                try:
                    next_url = urljoin(current_url, location)
                except ValueError as exc:
                    raise SourceNotAllowed("La destination de redirection est invalide.") from exc
                self._source_for_url(next_url)
                current_url = next_url
                continue

            if response.status_code != 200:
                response.close()
                raise LiveResearchError(
                    f"La source officielle n’a pas fourni de document complet (HTTP {response.status_code})."
                )
            return response, source, current_url

        raise LiveResearchError("La source officielle dépasse la limite de redirections.")

    def _read_bounded(self, response: requests.Response, limit: int) -> bytes:
        """Bound decoded bytes even for chunked/compressed transfers; always close the socket."""
        try:
            length = response.headers.get("Content-Length")
            if length is not None:
                try:
                    announced = int(length)
                    if announced < 0:
                        raise ValueError("Negative length")
                except ValueError as exc:
                    raise LiveResearchError(
                        "La taille annoncée par la source est invalide."
                    ) from exc
                if announced > limit:
                    raise DocumentTooLarge("Le téléchargement dépasse la taille autorisée.")
            deadline = time.monotonic() + self.timeout
            content = bytearray()
            for chunk in response.iter_content(chunk_size=STREAM_CHUNK_BYTES):
                if time.monotonic() > deadline:
                    raise LiveResearchError("Le délai de téléchargement est dépassé.")
                if len(content) + len(chunk) > limit:
                    raise DocumentTooLarge("Le téléchargement dépasse la taille autorisée.")
                content.extend(chunk)
            if (
                length is not None
                and not response.headers.get("Content-Encoding")
                and len(content) != announced
            ):
                raise LiveResearchError("Le téléchargement du document est incomplet.")
            return bytes(content)
        except requests.RequestException as exc:
            raise LiveResearchError("Le téléchargement a échoué ou a été interrompu.") from exc
        finally:
            response.close()

    @staticmethod
    def _decode_html(content: bytes, response: requests.Response) -> str:
        # Decode only after the bounded transfer; retain an explicit HTTP charset when present.
        decoded = requests.Response()
        decoded._content = content
        decoded.encoding = requests.utils.get_encoding_from_headers(
            requests.structures.CaseInsensitiveDict(response.headers)
        )
        if "charset=" not in response.headers.get("Content-Type", "").lower():
            decoded.encoding = None
        return decoded.text

    def search(
        self,
        query: str,
        *,
        source_ids: list[str] | tuple[str, ...],
        limit: int = MAX_RESULTS,
    ) -> tuple[SearchResult, ...]:
        if not query.strip():
            raise LiveResearchError("La recherche documentaire ne peut pas être vide.")
        limit = max(1, min(limit, MAX_RESULTS))
        selected: list[Source] = []
        for source_id in source_ids:
            source = self.sources.get(source_id)
            if source is None or not source.live_research:
                continue
            selected.append(source)
        if not selected:
            raise SourceNotAllowed("No allowed source selected for live search")

        domains = sorted({domain for source in selected for domain in source.allowed_domains})
        site_filter = " OR ".join(f"site:{domain}" for domain in domains)
        search_query = f"({site_filter}) {query.strip()}"
        try:
            response = self.session.get(
                DISCOVERY_URL,
                params={"q": search_query},
                headers={"User-Agent": "ACFPF/0.3 live-research"},
                timeout=self.timeout,
                allow_redirects=False,
                stream=True,
            )
        except requests.RequestException as exc:
            raise LiveResearchError("L’index de découverte est indisponible ou trop lent.") from exc
        if response.status_code != 200:
            response.close()
            raise LiveResearchError(
                f"L’index de découverte est indisponible (HTTP {response.status_code})."
            )
        if (
            response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            not in HTML_CONTENT_TYPES
        ):
            response.close()
            raise LiveResearchError("L’index de découverte n’a pas renvoyé de page HTML.")
        content = self._read_bounded(response, MAX_DISCOVERY_BYTES)
        html = self._decode_html(content, response)

        selected_ids = {item.id for item in selected}
        found: list[SearchResult] = []
        seen: set[str] = set()
        for raw_url, title in _parse_search_results(html):
            try:
                url = _redirect_target(urljoin(DISCOVERY_URL, raw_url))
                source = self._source_for_url(url)
            except (SourceNotAllowed, ValueError):
                continue
            if source.id not in selected_ids or url in seen:
                continue
            seen.add(url)
            found.append(SearchResult(source_id=source.id, title=title or url, url=url))
            if len(found) >= limit:
                break
        return tuple(found)

    def open(self, url: str) -> LiveDocument:
        response, source, final_url = self._get_official(url)
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type == "application/pdf":
            normalized_type = "application/pdf"
            limit = MAX_PDF_BYTES
        elif content_type in HTML_CONTENT_TYPES:
            normalized_type = "text/html"
            limit = MAX_HTML_BYTES
        else:
            response.close()
            raise LiveResearchError(
                "Le type de document n’est pas pris en charge (HTML ou PDF requis)."
            )
        content = self._read_bounded(response, limit)
        try:
            if normalized_type == "application/pdf":
                if not content.startswith(b"%PDF-"):
                    raise LiveResearchError("Le contenu reçu n’est pas un PDF valide.")
                units = _pdf_units(content)
                title = urlparse(final_url).path.rsplit("/", 1)[-1] or final_url
            else:
                html = self._decode_html(content, response)
                if not re.search(
                    r"<(?:!doctype\s+html|html|head|body|title|p|article|div|section)\b",
                    html,
                    re.IGNORECASE,
                ):
                    raise LiveResearchError("Le contenu reçu n’est pas un document HTML lisible.")
                text = extract_html_text(html)
                if len(text) > MAX_EXTRACTED_CHARS:
                    raise DocumentTooLarge("Le texte HTML dépasse la limite de lecture.")
                units = _split_html_units(text)
                title = _html_title(html, final_url)
        except LiveResearchError:
            raise
        except Exception as exc:
            # Malformed/encrypted PDF and extraction errors are recoverable source failures.
            raise LiveResearchError(
                "Le document officiel est invalide ou impossible à extraire."
            ) from exc

        if not units:
            raise LiveResearchError(
                "Le document ne contient aucun texte lisible. Les PDF nécessitant un OCR ne sont pas pris en charge."
            )

        self._document_counter += 1
        document_id = f"D{self._document_counter}"
        document = LiveDocument(
            document_id=document_id,
            source_id=source.id,
            title=title,
            url=final_url,
            retrieved_at=datetime.now(UTC).isoformat(),
            sha256=hashlib.sha256(content).hexdigest(),
            content_type=normalized_type,
            units=units,
        )
        self._documents[document_id] = document
        return document

    def read(self, document_id: str, unit_index: int) -> DocumentUnit:
        document = self._documents.get(document_id)
        if document is None:
            raise LiveResearchError(f"Unknown live document: {document_id}")
        for unit in document.units:
            if unit.index == unit_index:
                return unit
        raise LiveResearchError(
            f"Unit {unit_index} is outside document {document_id} (1-{len(document.units)})"
        )

    def document(self, document_id: str) -> LiveDocument:
        try:
            return self._documents[document_id]
        except KeyError as exc:
            raise LiveResearchError(f"Unknown live document: {document_id}") from exc
