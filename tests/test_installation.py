# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from importlib.resources import files
from pathlib import Path

from acfpf.source_registry import load_source_map, load_sources
from acfpf.web import create_app


def test_bundled_allowlist_matches_canonical_registry():
    canonical = Path(__file__).resolve().parents[1] / "config/sources.yml"
    assert files("acfpf").joinpath("resources/sources.yml").read_bytes() == canonical.read_bytes()


def test_application_starts_outside_checkout_and_ignores_incidental_allowlist(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config").mkdir()
    (tmp_path / "config/sources.yml").write_text("sources: []")
    monkeypatch.setenv("ACFPF_LLM_PROVIDER", "gemini")
    monkeypatch.delenv("ACFPF_LLM_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert "insee" in load_source_map()
    client = create_app().test_client()
    home = client.get("/")
    assert home.status_code == 200
    assert "IA non configurée" in home.get_data(as_text=True)
    assert client.get("/static/js/research_stream.js").status_code == 200
    assert client.get("/static/css/tokens.css").status_code == 200


def test_explicit_registry_remains_supported(tmp_path):
    custom = tmp_path / "custom.yml"
    custom.write_text("sources: []")
    assert load_sources(custom) == []
