#!/usr/bin/env python3
"""
scripts/record_demo_screen.py
==============================
Automated high-definition screen recorder for MusePilot championship submission.

Strictly aligned with user requirements and docs/DEMO_AND_SUBMISSION_PLAYBOOK.md:
  1. Fullscreen Chrome Mode - Native edge-to-edge application presentation
  2. Mobile Demo with LIVE Device View - Clean phone screen mirror + SAM 3.1 toggle
  3. Fleet Management - Live Samsung Galaxy S24 Ultra hardware mirror & 1:1 touch surface
  4. Opaque HTML5 Canvas Calibration - Live canvas view & Set-of-Mark grounding
  5. Incident Triage & Self-Healing - Live modal obstruction popup & Cyber Purple replan
  6. Developer Hub & Cloud Shell Drawer - Live CLI terminal & MCP server
  7. Metrics Intelligence - 100% Invariant Target Met & Multi-Model Inference SLAs
  8. Championship Close on Mission Control HUD

Output: demo/musepilot_demo_recording.mp4 (1080p60 H.264)
"""

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

import requests
import websockets

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FFMPEG_BIN = (
    PROJECT_ROOT
    / ".venv/lib/python3.14/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1"
)
OUTPUT_DIR = PROJECT_ROOT / "demo"
OUTPUT_VIDEO = OUTPUT_DIR / "musepilot_demo_recording.mp4"
RAW_VIDEO = Path("/tmp/raw_demo_recording.mov")

RECORDING_DURATION_SEC = 90


def set_chrome_fullscreen():
    """Ensure Google Chrome is active and in true native macOS fullscreen mode."""
    script = """
    tell application "Google Chrome" to activate
    delay 0.5
    tell application "System Events"
        keystroke "f" using {control down, command down}
    end tell
    """
    subprocess.run(["/usr/bin/osascript", "-e", script], check=False)
    time.sleep(1.0)


async def execute_cdp_action(ws, expr, description=""):
    """Run a JavaScript expression in the Chrome tab via CDP."""
    payload = {
        "id": int(time.time() * 1000) % 1000000,
        "method": "Runtime.evaluate",
        "params": {
            "expression": expr,
            "returnByValue": True,
        },
    }
    await ws.send(json.dumps(payload))
    raw = await ws.recv()
    resp = json.loads(raw)
    result = resp.get("result", {}).get("result", {}).get("value")
    print(f"  [CDP] {description} -> {result}")
    return result


async def click_semantic_by_query(ws, query, description=""):
    """Robustly find and click a leaf semantic element matching query text."""
    expr = f"""
    (() => {{
        const host = document.querySelector('flt-semantics-host') || document.body;
        const all = Array.from(host.querySelectorAll('*'));
        const matches = all.filter(el => {{
            const t = (el.getAttribute('aria-label') || el.innerText || '').toLowerCase();
            return t.includes('{query.lower()}');
        }});
        if (matches.length === 0) return 'Query \"{query}\" not found';
        matches.sort((a, b) => {{
            const ta = a.getAttribute('aria-label') || a.innerText || '';
            const tb = b.getAttribute('aria-label') || b.innerText || '';
            return ta.length - tb.length;
        }});
        const best = matches[0];
        best.click();
        return 'Clicked: ' + (best.getAttribute('aria-label') || best.innerText || best.id).slice(0, 50);
    }})()
    """
    desc = description or f"Click '{query}'"
    return await execute_cdp_action(ws, expr, desc)


async def wait_until_workflow_completed(ws, timeout=12.0):
    """Wait until the Run workflow button returns from Running to idle."""
    check_expr = """
    (() => {
        const host = document.querySelector('flt-semantics-host') || document.body;
        const text = host.innerText || '';
        return text.includes('Running workflow');
    })()
    """
    start = time.time()
    while time.time() - start < timeout:
        is_running = await execute_cdp_action(ws, check_expr, "Check if running")
        if not is_running:
            print("  ✔ Workflow completed.")
            return True
        await asyncio.sleep(0.5)
    print("  ⚠ Timeout waiting for workflow completion.")
    return False


async def run_storyboard(ws_url):
    """Execute the choreographed sequence across the Flutter Web HUD."""
    print("▶ Connecting to Chrome DevTools Protocol at:", ws_url)
    async with websockets.connect(ws_url) as ws:
        # Initialize semantics if placeholder exists
        init_expr = """
        (() => {
            const ph = document.querySelector('flt-semantics-placeholder');
            if (ph) ph.click();
            return 'Semantics initialized';
        })()
        """
        await execute_cdp_action(ws, init_expr, "Initialize Accessibility")
        await asyncio.sleep(2.0)

        # -------------------------------------------------------------
        # PHASE 1: Fullscreen Mission Control Overview
        # -------------------------------------------------------------
        print("\n🎬 PHASE 1: Fullscreen Mission Control & Zero-Coordinate Invariant")
        await click_semantic_by_query(ws, "Mission", "Mission Tab 0")
        await asyncio.sleep(3.0)

        # -------------------------------------------------------------
        # PHASE 2: Demo 1 — Live Android Automation with LIVE Device View
        # -------------------------------------------------------------
        print("\n🎬 PHASE 2: Demo 1 — Mobile Demo with LIVE Device View (Samsung S24 Ultra)")
        print("  → Selecting Android mobile agent scenario...")
        await click_semantic_by_query(ws, "Android mobile agent", "Android Mobile Agent Scenario")
        await asyncio.sleep(2.0)

        # Switch to Live Device View / Live Mirror to show real phone screen
        print("  📱 Switching to Device View / Live Mirror (Live Phone Screen)...")
        res = await click_semantic_by_query(ws, "Mirror", "Live Mirror Toggle")
        if "not found" in str(res).lower():
            await click_semantic_by_query(ws, "Device View", "Device View Toggle")
        await asyncio.sleep(2.5)

        print("  → Triggering Android ADB Workflow over live phone screen...")
        await click_semantic_by_query(ws, "Run workflow", "Run Workflow Button")
        await wait_until_workflow_completed(ws, timeout=12.0)
        await asyncio.sleep(3.0)  # Appreciate verified live phone screen

        # Toggle to SAM Grounding to reveal sub-pixel Set-of-Mark badges
        print("  🎯 Toggling to SAM Grounding to show Set-of-Mark radar badges...")
        await click_semantic_by_query(ws, "SAM Grounding", "SAM Grounding Toggle")
        await asyncio.sleep(3.0)

        # -------------------------------------------------------------
        # PHASE 3: Fleet Management — Live Hardware Screen Mirror
        # -------------------------------------------------------------
        print("\n🎬 PHASE 3: Fleet Management & Hardware Touch Surface")
        await click_semantic_by_query(ws, "Fleet", "Fleet Tab 1")
        await asyncio.sleep(6.5)

        # -------------------------------------------------------------
        # PHASE 4: Demo 2A — Opaque HTML5 Canvas Calibration (Zero DOM Nodes)
        # -------------------------------------------------------------
        print("\n🎬 PHASE 4: Demo 2A — Opaque HTML5 Canvas Calibration (Zero DOM Nodes)")
        await click_semantic_by_query(ws, "Mission", "Return to Mission Control")
        await asyncio.sleep(1.5)

        print("  → Selecting Canvas and creative tools scenario...")
        await click_semantic_by_query(
            ws, "Canvas and creative tools", "Canvas & Creative Tools Scenario"
        )
        await asyncio.sleep(2.0)

        # Show live canvas view
        print("  🎨 Switching to Device View to inspect live WebGL canvas...")
        await click_semantic_by_query(ws, "Device View", "Device View Toggle")
        await asyncio.sleep(2.0)

        # Show SAM Grounding radar
        print("  🎯 Switching to SAM Grounding to show mask overlays [01]-[04]...")
        await click_semantic_by_query(ws, "SAM Grounding", "SAM Grounding Toggle")
        await asyncio.sleep(2.0)

        print("  → Triggering Precision Canvas Calibration...")
        await click_semantic_by_query(ws, "Run workflow", "Run Workflow Button")
        await wait_until_workflow_completed(ws, timeout=12.0)
        await asyncio.sleep(3.0)

        # -------------------------------------------------------------
        # PHASE 5: Demo 2B — Autonomous Incident Triage & Modal Self-Healing
        # -------------------------------------------------------------
        print("\n🎬 PHASE 5: Demo 2B — Autonomous Incident Triage & Modal Recovery")
        print("  → Selecting Incident triage and self-healing scenario...")
        await click_semantic_by_query(
            ws, "Incident triage", "Incident Triage & Self-Healing Scenario"
        )
        await asyncio.sleep(2.0)

        print("  📱 Switching to Device View to show live blocking modal popup...")
        await click_semantic_by_query(ws, "Device View", "Device View Toggle")
        await asyncio.sleep(2.0)

        print("  → Triggering Self-Healing Modal Replan...")
        await click_semantic_by_query(ws, "Run workflow", "Run Workflow Button")
        await wait_until_workflow_completed(ws, timeout=12.0)
        await asyncio.sleep(2.5)

        print("  🎯 Toggling to SAM Grounding to show Cyber Purple replan branch...")
        await click_semantic_by_query(ws, "SAM Grounding", "SAM Grounding Toggle")
        await asyncio.sleep(3.0)

        # -------------------------------------------------------------
        # PHASE 6: Under the Hood — Developer Hub & Live Cloud Shell Drawer (MCP)
        # -------------------------------------------------------------
        print("\n🎬 PHASE 6: Under the Hood — Developer Hub & Live Cloud Shell Drawer")
        await click_semantic_by_query(ws, "SDK Hub", "SDK Hub Tab 2")
        await asyncio.sleep(3.5)

        print("  🖥️ Opening Slide-over Cloud Shell Terminal...")
        await click_semantic_by_query(ws, "MusePilot cli", "Open CLI Drawer")
        await asyncio.sleep(6.0)

        print("  🖥️ Closing Cloud Shell Terminal...")
        await click_semantic_by_query(ws, "MusePilot cli", "Close CLI Drawer")
        await asyncio.sleep(1.5)

        # -------------------------------------------------------------
        # PHASE 7: Metrics Intelligence & Multi-Model Inference SLAs
        # -------------------------------------------------------------
        print("\n🎬 PHASE 7: Metrics Intelligence & Multi-Model Inference SLAs")
        await click_semantic_by_query(ws, "Metrics", "Metrics Tab 4")
        await asyncio.sleep(7.5)

        # -------------------------------------------------------------
        # PHASE 8: Championship Close on Mission Control HUD
        # -------------------------------------------------------------
        print("\n🎬 PHASE 8: Triumphant Close on Mission Control HUD")
        await click_semantic_by_query(ws, "Mission", "Mission Tab 0")
        await asyncio.sleep(4.0)

        print("✔ Full championship storyboard completed successfully!")


def main():
    print("=" * 70)
    print("🏆 MUSEPILOT FULLSCREEN CHAMPIONSHIP DEMO RECORDER")
    print("=" * 70)

    # 1. Verify environment
    if not FFMPEG_BIN.exists():
        print(f"❌ FFmpeg binary not found at {FFMPEG_BIN}")
        sys.exit(1)

    # Clean previous raw recording
    if RAW_VIDEO.exists():
        RAW_VIDEO.unlink()

    # 2. Check Chrome CDP
    try:
        tabs = requests.get("http://127.0.0.1:9222/json/list", timeout=3).json()
        page_tab = next(t for t in tabs if t.get("type") == "page" and "8501" in t.get("url", ""))
        ws_url = page_tab["webSocketDebuggerUrl"]
    except Exception as e:
        print(f"❌ Failed to find MusePilot tab on CDP (port 9222): {e}")
        sys.exit(1)

    # 3. Ensure Chrome is in full screen mode
    print("🖥️ Setting Google Chrome to true native macOS fullscreen mode...")
    set_chrome_fullscreen()

    # 4. Launch screencapture in background
    print(f"\n🎥 Starting native macOS screencapture ({RECORDING_DURATION_SEC}s) -> {RAW_VIDEO}...")
    record_proc = subprocess.Popen(
        [
            "/usr/sbin/screencapture",
            "-v",
            "-k",
            "-C",
            f"-V{RECORDING_DURATION_SEC}",
            str(RAW_VIDEO),
        ]
    )

    # Allow screencapture to initialize
    time.sleep(1.5)

    # 5. Run the storyboard
    try:
        asyncio.run(run_storyboard(ws_url))
    except Exception as e:
        print(f"❌ Error during storyboard execution: {e}")

    # 6. Wait for screencapture to complete
    print(f"\n⏳ Finalizing screen recording (waiting for {RAW_VIDEO})...")
    record_proc.wait()
    time.sleep(1.0)

    if not RAW_VIDEO.exists():
        print(f"❌ Raw recording {RAW_VIDEO} was not produced!")
        sys.exit(1)

    raw_size_mb = RAW_VIDEO.stat().st_size / (1024 * 1024)
    print(f"✔ Raw recording captured: {raw_size_mb:.2f} MB")

    # 7. Transcode with FFmpeg to 1080p60 H.264
    print(f"\n⚙ Transcoding to {OUTPUT_VIDEO} (1920x1080 @ 60fps)...")
    ffmpeg_cmd = [
        str(FFMPEG_BIN),
        "-y",
        "-i",
        str(RAW_VIDEO),
        "-vf",
        "scale=1920:1080:flags=lanczos",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "19",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(OUTPUT_VIDEO),
    ]

    res = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"❌ FFmpeg error: {res.stderr}")
        sys.exit(1)

    # Clean raw recording
    RAW_VIDEO.unlink(missing_ok=True)

    out_size_mb = OUTPUT_VIDEO.stat().st_size / (1024 * 1024)
    print("=" * 70)
    print("🎉 FULLSCREEN DEMO SCREEN RECORDING COMPLETE!")
    print(f"📁 Video Path: {OUTPUT_VIDEO}")
    print(f"📊 Size: {out_size_mb:.2f} MB")
    print(f"⏱ Duration: ~{RECORDING_DURATION_SEC} seconds (1080p60)")
    print("=" * 70)


if __name__ == "__main__":
    main()
