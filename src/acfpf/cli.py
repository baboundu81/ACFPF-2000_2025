# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (C) 2026 ACFPF contributors

from __future__ import annotations

import argparse
import threading
import webbrowser

from acfpf.web import create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lance l'interface locale ACFPF.")
    parser.add_argument("--host", default="127.0.0.1", help="Adresse d'écoute locale.")
    parser.add_argument("--port", default=5000, type=int, help="Port HTTP local.")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Ne pas ouvrir automatiquement le navigateur.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Active le mode debug Flask pour le développement local.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    app = create_app()
    url = f"http://{args.host}:{args.port}/"

    if not args.no_browser:
        timer = threading.Timer(0.8, webbrowser.open, args=(url,))
        timer.daemon = True
        timer.start()

    print(f"ACFPF est disponible sur {url}")
    app.run(host=args.host, port=args.port, debug=args.debug, use_reloader=args.debug)
