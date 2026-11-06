# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors
"""Inspect actual Assembly Syceron XML ZIP before attributing debates to a dossier."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO

import pytest
import requests

DEBATE_ARCHIVE = (
    "https://data.assemblee-nationale.fr/static/openData/repository/"
    "17/VP/syceronbrut/syseron.xml.zip"
)


@pytest.mark.skipif(
    os.environ.get("ACFPF_LIVE_SOURCES") != "1",
    reason="Live official source checks require explicit opt-in",
)
def test_live_syceron_xml_debate_archive_schema():
    response = requests.get(DEBATE_ARCHIVE, timeout=(20, 180))
    response.raise_for_status()
    assert response.content[:2] == b"PK"
    assert len(response.content) < 120 * 1024 * 1024
    with zipfile.ZipFile(BytesIO(response.content)) as archive:
        members = [info for info in archive.infolist() if info.filename.endswith(".xml")]
        assert members, "No XML debate records from official Assembly ZIP"
        print("LIVE-DEBATES-ARCHIVE-BYTES:", len(response.content))
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
