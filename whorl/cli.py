"""whorl CLI — `whorl up` runs the dev server."""

from __future__ import annotations

import argparse

import uvicorn

from whorl import __version__
from whorl.app import create_app
from whorl.config import get_settings


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="whorl",
        description="Open-source crop-scouting dashboard for Midwest farmers and agronomists.",
    )
    parser.add_argument("--version", action="version", version=f"whorl {__version__}")
    sub = parser.add_subparsers(dest="command")

    up = sub.add_parser("up", help="Run the whorl server and serve the UI.")
    up.add_argument("--host", default="127.0.0.1")
    up.add_argument("--port", type=int, default=None)

    args = parser.parse_args(argv)

    settings = get_settings()
    host = getattr(args, "host", "127.0.0.1")
    port = getattr(args, "port", None) or settings.whorl_port

    app = create_app(settings)
    print(f"whorl {__version__}  →  http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
