# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors
"""Byte-range transport never accepts partial or tampered official XML archives."""

import zipfile
from io import BytesIO

import pytest
import requests

from acfpf.data.assemblee_debates import (
    DEBATES_ARCHIVE_URL,
    DebateArchiveError,
    download_debate_archive,
)


def make_zip():
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("seances/2026-11-01.xml", "<seance><titre>Test officiel</titre></seance>")
    return buffer.getvalue()


class FakeResponse:
    def __init__(self, *, status=200, headers=None, content=b""):
        self.status_code = status
        self.headers = headers or {}
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def iter_content(self, chunk_size):
        for i in range(0, len(self.content), chunk_size):
            yield self.content[i:i + chunk_size]


class FakeSession:
    def __init__(self, blob):
        self.blob = blob
        self.heads = []
        self.ranges = []
        self.corrupt_range = False
        self.partial_first = False
        self.partial_count = 0

    def head(self, url, **kwargs):
        assert url == DEBATES_ARCHIVE_URL
        assert kwargs["allow_redirects"] is False
        self.heads.append(url)
        return FakeResponse(headers={
            "Content-Length": str(len(self.blob)), "Accept-Ranges": "bytes",
        })

    def get(self, url, **kwargs):
        assert url == DEBATES_ARCHIVE_URL
        assert kwargs["allow_redirects"] is False
        assert kwargs["stream"] is True
        requested = kwargs["headers"]["Range"]
        self.ranges.append(requested)
        part = requested.removeprefix("bytes=")
        start, end = map(int, part.split("-"))
        if self.corrupt_range:
            return FakeResponse(
                status=206,
                headers={"Content-Range": f"bytes {start + 1}-{end}/{len(self.blob)}"},
                content=self.blob[start:end + 1],
            )
        chunk = self.blob[start:end + 1]
        if self.partial_first and start == 0 and self.partial_count == 0:
            self.partial_count += 1
            chunk = chunk[:-1]
        return FakeResponse(
            status=206,
            headers={"Content-Range": f"bytes {start}-{end}/{len(self.blob)}"},
            content=chunk,
        )


def test_bounded_ranges_download_and_validated_cache_reuse(tmp_path):
    source = FakeSession(make_zip())
    path = tmp_path / "cache" / "debates.zip"
    result = download_debate_archive(cache_path=path, session=source, range_bytes=19)
    assert result.path == path
    assert result.source_url == DEBATES_ARCHIVE_URL
    assert result.from_cache is False
    assert path.read_bytes() == source.blob
    assert source.heads == [DEBATES_ARCHIVE_URL]
    assert all("bytes=" in item for item in source.ranges)
    again = download_debate_archive(cache_path=path, session=source)
    assert again.from_cache is True
    assert source.heads == [DEBATES_ARCHIVE_URL]


def test_incomplete_range_is_retried_without_accepting_corrupt_bytes(tmp_path):
    source = FakeSession(make_zip())
    source.partial_first = True
    result = download_debate_archive(
        cache_path=tmp_path / "archive.zip", session=source, range_bytes=40,
    )
    assert result.path.read_bytes() == source.blob
    assert source.partial_count == 1
    assert source.ranges[:2] == ["bytes=0-39", "bytes=0-39"]


def test_wrong_content_range_is_rejected_and_partial_cache_removed(tmp_path):
    source = FakeSession(make_zip())
    source.corrupt_range = True
    path = tmp_path / "archive.zip"
    with pytest.raises(DebateArchiveError, match="identity mismatch"):
        download_debate_archive(cache_path=path, session=source, range_bytes=40)
    assert not path.exists()
    assert not path.with_suffix(".part").exists()


def test_zip_crc_or_member_validation_cannot_be_silently_skipped(tmp_path):
    source = FakeSession(b"PKnot-valid-zip")
    with pytest.raises(DebateArchiveError, match="unreadable"):
        download_debate_archive(
            cache_path=tmp_path / "archive.zip", session=source, range_bytes=20,
        )


def test_network_outage_falls_back_only_to_verified_cached_zip(tmp_path):
    class BrokenSession:
        def head(self, url, **kwargs):
            raise requests.ConnectionError("simulated")

    path = tmp_path / "archive.zip"
    path.write_bytes(make_zip())
    fallback = download_debate_archive(
        cache_path=path, session=BrokenSession(), refresh=True,
    )
    assert fallback.from_cache
    path.write_bytes(b"garbage")
    with pytest.raises(DebateArchiveError):
        download_debate_archive(cache_path=path, session=BrokenSession(), refresh=True)


def test_range_block_size_is_bounded(tmp_path):
    with pytest.raises(DebateArchiveError, match="block size"):
        download_debate_archive(cache_path=tmp_path / "unused", range_bytes=0)
