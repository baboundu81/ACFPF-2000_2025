# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors
"""Inspect actual Assembly Syceron XML ZIP before attributing debates to a dossier."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
import zipfile

import pytest
import requests

from acfpf.data.assemblee_debates import DEBATES_ARCHIVE_URL, download_debate_archive

DEBATE_ARCHIVE = DEBATES_ARCHIVE_URL


@pytest.mark.skipif(
    os.environ.get("ACFPF_LIVE_SOURCES") != "1",
    reason="Live official source checks require explicit opt-in",
)
def test_official_syceron_transport_headers():
    # Cheap transport smoke test; does not claim to have parsed the archive.
    response = requests.head(DEBATE_ARCHIVE, timeout=(10, 30), allow_redirects=False)
    assert response.status_code == 200
    print("LIVE-DEBATES-CONTENT-LENGTH:", response.headers.get("Content-Length"))
    print("LIVE-DEBATES-ACCEPT-RANGES:", response.headers.get("Accept-Ranges"))
    with requests.get(
        DEBATE_ARCHIVE, headers={"Range": "bytes=0-2047"},
        timeout=(10, 30), stream=True, allow_redirects=False,
    ) as sample:
        assert sample.status_code in {200, 206}
        signature = next(sample.iter_content(chunk_size=512), b"")
        assert signature.startswith(b"PK")
        print("LIVE-DEBATES-RANGE-STATUS:", sample.status_code)


@pytest.mark.skipif(
    os.environ.get("ACFPF_LIVE_DEBATES_FULL") != "1",
    reason="Large XML archive verification is a separate network-intensive opt-in",
)
def test_live_syceron_xml_debate_archive_schema(tmp_path):
    downloaded = download_debate_archive(
        cache_path=tmp_path / "official_debates.zip", refresh=True,
    )
    assert downloaded.bytes_downloaded < 120 * 1024 * 1024
    with zipfile.ZipFile(downloaded.path) as archive:
        members = [info for info in archive.infolist() if info.filename.endswith(".xml")]
        assert members, "No XML debate records from official Assembly ZIP"
        print("LIVE-DEBATES-ARCHIVE-BYTES:", downloaded.bytes_downloaded)
        print("LIVE-DEBATES-XML-MEMBERS:", len(members))
        print("LIVE-DEBATES-SAMPLE-MEMBERS:", [
            (info.filename, info.file_size) for info in members[:5]
        ])
        first = min(members, key=lambda info: info.file_size)
        with archive.open(first) as reader:
            prefix = reader.read(500_000)
        parser = ET.XMLPullParser(events=("start",))
        parser.feed(prefix)
        elements = []
        for _, element in parser.read_events():
            tag = element.tag.split("}")[-1]
            if len(elements) < 50:
                elements.append((tag, sorted(element.attrib)))
        print("LIVE-DEBATES-SAMPLE-PATH:", first.filename)
        print("LIVE-DEBATES-ELEMENTS:", elements[:30])
        print("LIVE-DEBATES-LINK-TOKENS:", {
            token: prefix.lower().count(token.lower())
            for token in (b"dossierRef", b"texteRef", b"texteAssocie", b"uid", b"seance", b"intervention")
        })
        assert elements
