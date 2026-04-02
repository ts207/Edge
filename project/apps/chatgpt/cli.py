from __future__ import annotations

import argparse
import json
import sys

from project.apps.chatgpt.backlog import IMPLEMENTATION_BACKLOG
from project.apps.chatgpt.resources import build_widget_resource
from project.apps.chatgpt.server import build_server_blueprint, serve_streamable_http


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="edge-chatgpt-app",
        description="Scaffolding and inspection helpers for the Edge ChatGPT app surface.",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("backlog", help="Print the current implementation backlog as JSON.")
    subparsers.add_parser("blueprint", help="Print the current server blueprint as JSON.")
    subparsers.add_parser("widget", help="Print the widget resource payload as JSON.")

    serve_parser = subparsers.add_parser("serve", help="Attempt to start the live MCP server scaffold.")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)
    serve_parser.add_argument("--path", default="/mcp")

    subparsers.required = True
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "backlog":
        print(json.dumps(list(IMPLEMENTATION_BACKLOG), indent=2, sort_keys=True))
        return 0

    if args.command == "blueprint":
        print(json.dumps(build_server_blueprint(), indent=2, sort_keys=True))
        return 0

    if args.command == "widget":
        print(json.dumps(build_widget_resource(), indent=2, sort_keys=True))
        return 0

    if args.command == "serve":
        serve_streamable_http(host=args.host, port=args.port, path=args.path)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
