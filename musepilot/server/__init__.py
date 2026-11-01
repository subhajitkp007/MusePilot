# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Starlette JSON API and WebSocket server for cross-platform HUD clients."""

from __future__ import annotations

from musepilot.server.app import app, create_app, main

__all__ = ["app", "create_app", "main"]
