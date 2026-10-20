# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from acfpf.macro import build_dashboard
from tests.test_eurostat import sample_dataset


def test_dashboard_builds_kpis_and_rows() -> None:
    dashboard = build_dashboard(sample_dataset())
    payload = dashboard.as_dict()

    expenditure = next(kpi for kpi in payload["kpis"] if kpi["key"] == "expenditure")
    revenue = next(kpi for kpi in payload["kpis"] if kpi["key"] == "revenue")

    assert expenditure["value"] == 57.3
    assert expenditure["delta"] == 4.7
    assert revenue["delta"] == 0.9
    assert payload["rows"][0]["year"] == 2000
    assert payload["rows"][-1]["year"] == 2025
    assert payload["rows"][-1]["debt"] == 113.0
    assert "+4.7" in payload["insight"]
