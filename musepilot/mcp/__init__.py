# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Model Context Protocol (MCP) server for MusePilot.

Exposes visual grounding (Meta SAM 3.1), autonomous multimodal planning
(Muse Spark), open-weight verification (muse-spark-open-1026), and device actuation
as standard MCP tools, resources, and prompt templates.
"""

from __future__ import annotations

from musepilot.mcp.server import create_mcp_server, run_mcp_server

__all__ = ["create_mcp_server", "run_mcp_server"]
