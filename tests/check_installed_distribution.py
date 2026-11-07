# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

"""Run with an installed wheel's Python -I, outside the checkout (no network)."""

from importlib.metadata import version

from acfpf import __version__
from acfpf.source_registry import load_sources
from acfpf.web import create_app


def main():
    assert version("acfpf") == __version__
    assert any(source.id == "insee" for source in load_sources())
    client = create_app().test_client()
    for route in [
        "/",
        "/healthz",
        "/api/evidence",
        "/static/css/tokens.css",
        "/static/css/legislation.css",
        "/static/js/research_stream.js",
        "/static/js/ask.js",
    ]:
        response = client.get(route)
        assert response.status_code == 200, (route, response.status_code)
    assert client.get("/healthz").json["status"] == "ok"
    print(f"Installed distribution {__version__}: registry, routes and assets OK")


if __name__ == "__main__":
    main()
