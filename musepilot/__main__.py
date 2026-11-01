# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Module execution entry point for python -m musepilot."""

from __future__ import annotations

import sys

from musepilot.cli import main

if __name__ == "__main__":
    sys.exit(main())
