# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

import pytest

from acfpf.data.assemblee_amendment_detail import (
    AssemblyAmendmentDetailError,
    fetch_assembly_amendment_xml,
    parse_assembly_amendment_xml,
)


def sample_xml(uid: str = "AMANR5L17N000042") -> bytes:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<amendement xmlns="http://schemas.assemblee-nationale.fr/referentiel">
  <uid>{uid}</uid>
  <triAmendement>000042</triAmendement>
  <corps>
    <contenuAuteur>
      <dispositif>&lt;p&gt;Remplacer le taux de 15 % par le taux de 12 %.&lt;/p&gt;</dispositif>
      <exposeSommaire>&lt;p&gt;Cet amendement vise à limiter la hausse proposée.&lt;/p&gt;</exposeSommaire>
    </contenuAuteur>
  </corps>
</amendement>
""".encode()


def test_parse_xml_extracts_and_cleans_dispositif_and_purpose() -> None:
    detail = parse_assembly_amendment_xml(
        sample_xml(),
        uid="AMANR5L17N000042",
        source_url="https://www.assemblee-nationale.fr/dyn/opendata/AMANR5L17N000042.xml",
        retrieved_at="2026-11-03T14:00:00+00:00",
    )

    assert detail.uid == "AMANR5L17N000042"
    assert detail.dispositif == "Remplacer le taux de 15 % par le taux de 12 %."
    assert detail.purpose == "Cet amendement vise à limiter la hausse proposée."
    assert detail.sort_order == "000042"


def test_parse_xml_rejects_mismatched_uid() -> None:
    with pytest.raises(AssemblyAmendmentDetailError, match="does not match"):
        parse_assembly_amendment_xml(
            sample_xml("AMANR5L17N999999"),
            uid="AMANR5L17N000042",
            source_url="https://www.assemblee-nationale.fr/dyn/opendata/AMANR5L17N000042.xml",
        )


def test_parse_xml_rejects_invalid_xml() -> None:
    with pytest.raises(AssemblyAmendmentDetailError, match="Unable to parse"):
        parse_assembly_amendment_xml(
            b"<amendement>",
            uid="AMANR5L17N000042",
            source_url="https://www.assemblee-nationale.fr/dyn/opendata/AMANR5L17N000042.xml",
        )


def test_fetch_rejects_non_official_url_before_network_call() -> None:
    with pytest.raises(AssemblyAmendmentDetailError, match="not an official"):
        fetch_assembly_amendment_xml("https://example.com/AMANR5L17N000042.xml")


def test_fetch_rejects_non_xml_official_url_before_network_call() -> None:
    with pytest.raises(AssemblyAmendmentDetailError, match="not an XML"):
        fetch_assembly_amendment_xml(
            "https://www.assemblee-nationale.fr/dyn/opendata/AMANR5L17N000042.pdf"
        )
