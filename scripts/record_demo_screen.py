#!/usr/bin/env python3
"""
scripts/record_demo_screen.py
==============================
Automated high-definition screen recorder for MusePilot championship submission.

Executes the complete 5-phase demo storyboard across Chrome and the Flutter HUD:
  1. Mission Control & Precision Canvas (W1) - Zero-Coordinate Invariant & SAM 3.1 Radar
  2. Incident Triage & Self-Healing (W2) - Modal Obstruction Detection & Cyber Purple Replan
  3. Fleet Management - Samsung Galaxy S24 Ultra Wireless ADB Actuation
  4. SDK Hub & Cloud Shell CLI - MCP Server Infrastructure & Live Terminal Drawer
  5. Metrics Intelligence - 100% Invariant Target Met & Multi-Model Inference Latency SLAs
  6. Championship Return to Mission Control

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

RECORDING_DURATION_SEC = 62


def activate_chrome():
    """Bring Google Chrome to front window."""
    script = 'tell application "Google Chrome" to activate'
    subprocess.run(["/usr/bin/osascript", "-e", script], check=False)
    time.sleep(0.5)


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


async def click_semantic_node(ws, node_id, description=""):
    """Click a specific Flutter semantic node by ID."""
    expr = f"""
    (() => {{
        const node = document.getElementById('{node_id}');
        if (node) {{
            node.click();
            return 'Clicked {node_id} ({description})';
        }}
        const host = document.querySelector('flt-semantics-host') || document.body;
        const candidates = Array.from(host.querySelectorAll('*'));
        const fallback = candidates.find(el => (el.innerText || el.getAttribute('aria-label') || '').includes('{description}'));
        if (fallback) {{
            fallback.click();
            return 'Clicked fallback for {description}';
        }}
        return 'Node {node_id} not found';
    }})()
    """
    return await execute_cdp_action(ws, expr, f"Click {description} [{node_id}]")


async def click_run_workflow(ws):
    """Click the Run Workflow button."""
    expr = """
    (() => {
        const btn = document.getElementById('flt-semantic-node-60') ||
                    document.getElementById('flt-semantic-node-61') ||
                    Array.from(document.querySelectorAll('*')).find(e => (e.innerText || e.getAttribute('aria-label') || '').trim() === 'Run workflow');
        if (btn) {
            btn.click();
            return 'Clicked Run workflow!';
        }
        return 'Run workflow button not found';
    })()
    """
    return await execute_cdp_action(ws, expr, "Click Run Workflow")


async def run_storyboard(ws_url):
    """Execute the choreographed sequence across the Flutter Web HUD."""
    print("▶ Connecting to Chrome DevTools Protocol at:", ws_url)
    async with websockets.connect(ws_url) as ws:
        # Initial stabilization
        await asyncio.sleep(2.0)

        # -------------------------------------------------------------
        # SCENE 1: Mission Control & Precision Canvas (W1)
        # -------------------------------------------------------------
        print("\n🎬 SCENE 1: Mission Control & Precision Canvas Calibration (W1)")
        await click_semantic_node(ws, "flt-semantic-node-5", "Mission Tab 0")
        await asyncio.sleep(1.8)

        print("  → Selecting Canvas and creative tools scenario...")
        await click_semantic_node(ws, "flt-semantic-node-43", "Canvas & Creative Tools Scenario")
        await asyncio.sleep(2.2)

        print("  → Triggering W1 Workflow (Zero-Coordinate Canvas Calibration)...")
        await click_run_workflow(ws)
        await asyncio.sleep(7.0)  # Stream all 4 steps
        await asyncio.sleep(2.5)  # Appreciate verified state

        # -------------------------------------------------------------
        # SCENE 2: Incident Triage & Self-Healing Replan (W2 Replan)
        # -------------------------------------------------------------
        print("\n🎬 SCENE 2: Incident Triage & Autonomous Modal Recovery (W2 Replan)")
        print("  → Selecting Incident triage and self-healing scenario...")
        await click_semantic_node(
            ws, "flt-semantic-node-45", "Incident Triage & Self-Healing Scenario"
        )
        await asyncio.sleep(2.2)

        print("  → Triggering W2 Replan Workflow (Modal Obstruction & Recovery)...")
        await click_run_workflow(ws)
        await asyncio.sleep(7.5)  # Modal detection, cache invalidation, replan, verification
        await asyncio.sleep(2.5)  # Appreciate recovered state

        # -------------------------------------------------------------
        # SCENE 3: Fleet Management Tab (Physical Samsung S24 Ultra)
        # -------------------------------------------------------------
        print("\n🎬 SCENE 3: Fleet Management & Wireless ADB Touch Surface")
        await click_semantic_node(ws, "flt-semantic-node-6", "Fleet Tab 1")
        await asyncio.sleep(6.0)

        # -------------------------------------------------------------
        # SCENE 4: SDK Hub & Cloud Shell Terminal Drawer
        # -------------------------------------------------------------
        print("\n🎬 SCENE 4: SDK Hub & Live MCP Terminal Drawer")
        await click_semantic_node(ws, "flt-semantic-node-7", "SDK Hub Tab 2")
        await asyncio.sleep(4.0)

        print("  → Opening Slide-over Cloud Shell Terminal...")
        await click_semantic_node(ws, "flt-semantic-node-10", "MusePilot CLI Drawer")
        await asyncio.sleep(5.5)

        print("  → Closing Cloud Shell Terminal...")
        await click_semantic_node(ws, "flt-semantic-node-10", "Close CLI Drawer")
        await asyncio.sleep(1.5)

        # -------------------------------------------------------------
        # SCENE 5: Metrics Intelligence & Telemetry Tab
        # -------------------------------------------------------------
        print("\n🎬 SCENE 5: Metrics Intelligence & Multi-Model Latency SLAs")
        await click_semantic_node(ws, "flt-semantic-node-9", "Metrics Tab 4")
        await asyncio.sleep(7.0)

        # -------------------------------------------------------------
        # SCENE 6: Return to Mission Control
        # -------------------------------------------------------------
        print("\n🎬 SCENE 6: Triumphant Close on Mission Control HUD")
        await click_semantic_node(ws, "flt-semantic-node-5", "Mission Tab 0")
        await asyncio.sleep(4.0)

        print("✔ Storyboard choreography completed successfully!")


def main():
    print("=" * 70)
    print("🏆 MUSEPILOT AUTOMATED SCREEN RECORDING PROTOCOL")
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

    # 3. Bring Chrome to front
    activate_chrome()

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
    print("🎉 DEMO SCREEN RECORDING COMPLETE!")
    print(f"📁 Video Path: {OUTPUT_VIDEO}")
    print(f"📊 Size: {out_size_mb:.2f} MB")
    print(f"⏱ Duration: ~{RECORDING_DURATION_SEC} seconds (1080p60)")
    print("=" * 70)


if __name__ == "__main__":
    main()
