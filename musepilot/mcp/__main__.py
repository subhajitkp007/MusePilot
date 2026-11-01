# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Main entry point for running MusePilot as an MCP server via stdio."""

from __future__ import annotations

import argparse
import sys

from musepilot.mcp.server import run_mcp_server


def main() -> None:
    """CLI entry point for python -m musepilot.mcp."""
    parser = argparse.ArgumentParser(
        prog="musepilot-mcp",
        description="MusePilot Model Context Protocol (MCP) server for AI assistants and agent frameworks.",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="MCP transport protocol (default: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8502,
        help="Port for SSE transport (default: 8502)",
    )
    args = parser.parse_args()

    try:
        run_mcp_server(
            transport=args.transport, port=args.port if args.transport == "sse" else None
        )
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
