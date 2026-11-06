# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors
"""Bounded resumable-by-range downloader for the official Assembly Syceron ZIP.

Every byte range is checked against Content-Range, not silently assembled from
untrusted or truncated responses. A fully validated ZIP atomically replaces cache.
"""

from __future__ import annotations

import os
import re
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import requests

DEBATES_ARCHIVE_URL = (
    "https://data.assemblee-nationale.fr/static/openData/repository/"
    "17/vp/syceronbrut/syseron.xml.zip"
)
DEBATES_CACHE_PATH = Path.home() / ".cache/acfpf/assembly_debates_17.zip"
MAX_COMPRESSED_BYTES = 120 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024
MAX_XML_MEMBERS = 20_000
_CHUNK_BYTES = 1024 * 1024
_CONTENT_RANGE = re.compile(r"bytes (\d+)-(\d+)/(\d+)\Z")


class DebateArchiveError(RuntimeError):
    """Official debate archive transport or integrity could not be verified."""


@dataclass(frozen=True)
class DebateArchive:
    path: Path
    source_url: str
    bytes_downloaded: int
    retrieved_at: str
    from_cache: bool


def _check_zip(path: Path) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if not members or len(members) > MAX_XML_MEMBERS:
                raise DebateArchiveError("Invalid official debate archive member count")
            if sum(info.file_size for info in members) > MAX_UNCOMPRESSED_BYTES:
                raise DebateArchiveError("Official archive uncompressed size exceeds limit")
            if not any(info.filename.endswith(".xml") for info in members):
                raise DebateArchiveError("Official archive contains no XML debates")
            if archive.testzip() is not None:
                raise DebateArchiveError("Official debate archive failed CRC validation")
    except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
        if isinstance(exc, DebateArchiveError):
            raise
        raise DebateArchiveError("Official debate ZIP is unreadable") from exc


def _archive(path: Path, *, from_cache: bool) -> DebateArchive:
    return DebateArchive(
        path=path,
        source_url=DEBATES_ARCHIVE_URL,
        bytes_downloaded=path.stat().st_size,
        retrieved_at=datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat(),
        from_cache=from_cache,
    )


def download_debate_archive(
    *, cache_path: Path = DEBATES_CACHE_PATH,
    refresh: bool = False,
    session: requests.Session | None = None,
    range_bytes: int = _CHUNK_BYTES,
) -> DebateArchive:
    """Acquire a complete official ZIP; never accept a partial response as valid.

    When the publisher changes the export during a download, Content-Range
    mismatches fail closed. Up to three attempts are made per small part.
    """
    if not 1 <= range_bytes <= 4 * 1024 * 1024:
        raise DebateArchiveError("Invalid range block size")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists() and not refresh:
        age = datetime.now(UTC).timestamp() - cache_path.stat().st_mtime
        if age < 24 * 60 * 60:
            try:
                _check_zip(cache_path)
                return _archive(cache_path, from_cache=True)
            except DebateArchiveError:
                pass

    client = session or requests.Session()
    temporary = cache_path.with_suffix(".part")
    try:
        with client.head(
            DEBATES_ARCHIVE_URL, timeout=(10, 40), allow_redirects=False
        ) as response:
            if response.status_code != 200:
                raise DebateArchiveError("Official debate archive HEAD is unavailable")
            try:
                length = int(response.headers.get("Content-Length", ""))
            except ValueError as exc:
                raise DebateArchiveError("Missing official archive byte length") from exc
            if length <= 0 or length > MAX_COMPRESSED_BYTES:
                raise DebateArchiveError("Official archive byte length exceeds limit")
            if "bytes" not in response.headers.get("Accept-Ranges", "").lower():
                raise DebateArchiveError("Official debate server does not advertise byte ranges")

        with temporary.open("wb") as target:
            for start in range(0, length, range_bytes):
                end = min(start + range_bytes, length) - 1
                required = end - start + 1
                succeeded = False
                for attempt in range(3):
                    try:
                        with client.get(
                            DEBATES_ARCHIVE_URL,
                            headers={"Range": f"bytes={start}-{end}"},
                            timeout=(10, 60), allow_redirects=False, stream=True,
                        ) as response:
                            if response.status_code != 206:
                                raise DebateArchiveError("Official server ignored exact byte range")
                            match = _CONTENT_RANGE.fullmatch(
                                response.headers.get("Content-Range", "")
                            )
                            if not match or tuple(map(int, match.groups())) != (
                                start, end, length
                            ):
                                raise DebateArchiveError("Official byte-range identity mismatch")
                            chunks = []
                            count = 0
                            for chunk in response.iter_content(chunk_size=65536):
                                count += len(chunk)
                                if count > required:
                                    raise DebateArchiveError("Byte range exceeded requested size")
                                chunks.append(chunk)
                            if count != required:
                                raise DebateArchiveError("Official byte range incomplete")
                            target.write(b"".join(chunks))
                            succeeded = True
                            break
                    except requests.RequestException as exc:
                        if attempt == 2:
                            raise DebateArchiveError("Official archive range download failed") from exc
                    except DebateArchiveError:
                        if attempt == 2:
                            raise
                if not succeeded:
                    raise DebateArchiveError("Official byte range unavailable")
        _check_zip(temporary)
        os.replace(temporary, cache_path)
        return _archive(cache_path, from_cache=False)
    except (OSError, requests.RequestException, DebateArchiveError) as exc:
        temporary.unlink(missing_ok=True)
        if cache_path.exists():
            try:
                _check_zip(cache_path)
                return _archive(cache_path, from_cache=True)
            except DebateArchiveError:
                pass
        if isinstance(exc, DebateArchiveError):
            raise
        raise DebateArchiveError("Unable to acquire official debate archive") from exc
