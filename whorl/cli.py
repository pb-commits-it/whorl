"""whorl CLI — `whorl up` runs the dev server; `whorl kb ingest` (re)builds the wiki."""

from __future__ import annotations

import argparse
import asyncio

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

    kb = sub.add_parser("kb", help="Knowledge-base maintenance commands.")
    kb_sub = kb.add_subparsers(dest="kb_command")
    kb_ingest = kb_sub.add_parser(
        "ingest", help="(Re)load the markdown wiki into the kb_chunks table."
    )
    kb_ingest.add_argument(
        "--database-url",
        default=None,
        help="Override Settings.database_url (defaults to the configured Postgres).",
    )

    weather = sub.add_parser("weather", help="Weather pipeline commands.")
    weather_sub = weather.add_subparsers(dest="weather_command")
    weather_sub.add_parser(
        "sync",
        help="Pre-fetch every field's forecast (run nightly by whorl-weather.timer).",
    )

    args = parser.parse_args(argv)

    if args.command == "kb" and args.kb_command == "ingest":
        from whorl.kb.ingest import main as kb_main

        asyncio.run(kb_main(database_url=args.database_url))
        return

    if args.command == "weather" and args.weather_command == "sync":
        from whorl.weather.sync import sync_all_fields

        asyncio.run(sync_all_fields())
        return

    # Default behavior: `whorl up` (no subcommand also runs the server).
    settings = get_settings()
    host = getattr(args, "host", "127.0.0.1")
    port = getattr(args, "port", None) or settings.whorl_port

    app = create_app(settings)
    print(f"whorl {__version__}  →  http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
