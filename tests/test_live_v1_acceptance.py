# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Bounded V1 acceptance cases; real provider and official HTTP, explicitly opted in."""

import json
import os

import pytest

from acfpf.web import create_app

CASES = [
    (
        "budget",
        (
            "Dans les series ACFPF, compare le solde public francais en 2000 et 2025. "
            "Donne les deux valeurs, la variation en points de PIB et la source. "
            "Ne conclus rien sur les causes."
        ),
    ),
    (
        "two_documents",
        (
            "Ouvre et lis ces deux pages officielles : "
            "https://www.assemblee-nationale.fr/dyn/17/dossiers/DLR5L17N54628 et "
            "https://www.senat.fr/dossier-legislatif/ppl25-800.html . "
            "Indique seulement leur titre et la nature du texte, avec une citation par page. "
            "Ne conclus rien sur le droit en vigueur."
        ),
    ),
]


@pytest.mark.skipif(
    os.environ.get("ACFPF_LIVE_ACCEPTANCE") != "1",
    reason="Real provider and official HTTP require ACFPF_LIVE_ACCEPTANCE=1",
)
@pytest.mark.parametrize("case_id,question", CASES, ids=[case[0] for case in CASES])
def test_live_v1_answer(case_id, question):
    response = create_app().test_client().post("/api/ask/stream", json={"question": question})
    events = [json.loads(line) for line in response.data.splitlines()]
    final = events[-1]
    print("LIVE-V1:", json.dumps({"case": case_id, "events": events}, ensure_ascii=False))
    assert final["type"] == "answer", "Provider or grounding error: see safe public events"
    answer = final["answer"]
    assert answer["status"] == "answered", "Evidence insufficient: acceptance remains open"
    citations = answer["citations"]
    assert citations
    if case_id == "two_documents":
        assert len({c["source_url"] for c in citations if c["evidence_id"]}) >= 2
        assert all(c["retrieved_at"] and c["sha256"] and c["locator"] for c in citations)
