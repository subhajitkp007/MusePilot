# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Pytest bootstrap: force hermetic simulated-mode runs with isolated storage."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_ISOLATED_ROOT = Path(tempfile.mkdtemp(prefix="musepilot_test_"))

# Pin deterministic test settings before any musepilot import reads them.
# This keeps the suite hermetic (no live API calls) and keeps run artifacts
# out of the repository's traces/, logs/, and demo/golden_traces/ directories.
os.environ["MUSEPILOT_EXECUTION_MODE"] = "simulated"
os.environ["MUSEPILOT_META_API_KEY"] = ""
os.environ["MUSEPILOT_PARTNER_API_KEY"] = ""
os.environ["MUSEPILOT_DISPLAY_DPI_SCALE"] = "2.0"
os.environ["MUSEPILOT_VERIFIER_MODEL_ID"] = "meta-models/muse-spark-open-1026"
os.environ["MUSEPILOT_TRACE_DIR"] = str(_ISOLATED_ROOT / "traces")
os.environ["MUSEPILOT_LOG_DIR"] = str(_ISOLATED_ROOT / "logs")
os.environ["MUSEPILOT_GOLDEN_TRACE_DIR"] = str(_ISOLATED_ROOT / "golden_traces")
