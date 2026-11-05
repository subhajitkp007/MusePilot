#!/usr/bin/env python3
"""
scripts/build_viral_x_video.py
==============================
Builds a high-impact 60-Second (60.0s) 1920x1080 Full HD Viral X (Twitter) Launch Video
for the Meta Global AI Developer Hackathon ($20,000 Most Viral Project Track):
  1. 8 Fast-Paced, Scroll-Stopping Visual Cuts (~7.5s per cut = 60.0s total)
  2. ElevenLabs Multilingual v2 Voiceover (Energetic Indian IT Architect persona)
  3. High-Contrast X/Twitter Autoplay Top Hook Pill + Lower-Third Closed Captions
  4. Exact 60.0-second (01:00) runtime in 1080p H.264 + AAC with embedded .srt subtitles
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FFMPEG_BIN = (
    PROJECT_ROOT
    / ".venv/lib/python3.14/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1"
)
CHROME_BIN = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
WORK_DIR = Path(
    "/Users/subhajitmahata/.gemini/antigravity/brain/9e06e823-7295-4596-9c21-ee4f8ce611eb/scratch/viral_x_video_build"
)
KEYNOTE_CACHE_DIR = Path(
    "/Users/subhajitmahata/.gemini/antigravity/brain/9e06e823-7295-4596-9c21-ee4f8ce611eb/scratch/video_build_v2"
)
OUTPUT_MP4 = PROJECT_ROOT / "demo/musepilot_viral_x_launch.mp4"
OUTPUT_SRT = PROJECT_ROOT / "demo/musepilot_viral_x_launch.srt"
WEB_MP4 = PROJECT_ROOT / "musepilot/server/static/web/assets/musepilot_viral_x_launch.mp4"

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
VOICE_ID = "onwK4e9ZLuTAKqWW03F9"
INDIAN_CONTEXT_PRIMING = (
    "Namaste everyone! Myself Subhajit Mahata, Principal AI Architect from Bengaluru, India."
)

VIRAL_SEGMENTS = [
    {
        "id": "viral_01_hook",
        "url": "http://127.0.0.1:8501/presentation.html?slide=1&scenario=retina&timer=01:00",
        "cached_base": KEYNOTE_CACHE_DIR / "seg_02a_base.png",
        "hook_tag": "🚨 WHY 90% OF AI GUI AGENTS FAIL IN PRODUCTION",
        "narration": (
            "Why do AI computer-use agents fail? Because vision models guess X-Y pixels and miss by twenty-four pixels!"
        ),
        "captions": [
            "🔥 Why do 90% of AI computer-use agents fail in production?",
            "Because LLMs guess raw [x, y] pixels—drifting by 24px on Retina 2.0× displays!",
        ],
    },
    {
        "id": "viral_02_canvas",
        "url": "http://127.0.0.1:8501/presentation.html?slide=1&scenario=canvas&timer=00:52",
        "cached_base": KEYNOTE_CACHE_DIR / "seg_02b_base.png",
        "hook_tag": "💥 0 DOM NODES = PLAYWRIGHT & SELENIUM CRASH",
        "narration": (
            "And on WebGL canvases like TradingView Pro, Playwright and Selenium crash because zero DOM nodes exist!"
        ),
        "captions": [
            "Even worse: on WebGL & HTML5 Canvas apps like TradingView Pro,",
            "Playwright and Selenium crash 100% of the time—0 DOM nodes exist!",
        ],
    },
    {
        "id": "viral_03_hero",
        "url": "http://127.0.0.1:8501/presentation.html?slide=0&timer=00:45",
        "cached_base": KEYNOTE_CACHE_DIR / "seg_01a_base.png",
        "hook_tag": "⚡ MEET MUSEPILOT: THE ZERO-COORDINATE AI AGENT",
        "narration": (
            "Meet MusePilot! Powered by four Meta AI models, we mathematically forbid the LLM from emitting raw coordinates."
        ),
        "captions": [
            "Meet MusePilot — powered by 4 native Meta AI models (SAM 3.1 + Muse Spark).",
            "Our Pydantic schema mathematically forbids the LLM from emitting raw [x, y] coordinates!",
        ],
    },
    {
        "id": "viral_04_stack",
        "url": "http://127.0.0.1:8501/presentation.html?slide=3&timer=00:37",
        "cached_base": KEYNOTE_CACHE_DIR / "seg_04_base.png",
        "hook_tag": "🧠 META SAM 3.1 + MUSE SPARK 1.3 + BASETEN OPEN WEIGHTS",
        "narration": (
            "Meta SAM 3.1 segments exact Set-of-Mark badges, Muse Spark plans by mask ID, and Baseten verifies every click."
        ),
        "captions": [
            "1️⃣ Meta SAM 3.1 segments exact Set-of-Mark badges ([01], [02]) with 0.0px drift.",
            "2️⃣ Muse Spark 1.3 plans by ID · 3️⃣ Muse Spark Open on Baseten verifies ROI pixel deltas!",
        ],
    },
    {
        "id": "viral_05_trading",
        "url": "http://127.0.0.1:8501/presentation.html?slide=4&modal=tradingview&timer=00:29",
        "cached_base": KEYNOTE_CACHE_DIR / "seg_05b_base.png",
        "hook_tag": "📈 LIVE DEMO 1: AUTONOMOUS TRADINGVIEW WEBGL EXECUTION",
        "narration": (
            "Watch MusePilot operate a live TradingView canvas: locking the four-hour chart, enabling EMA, and filling a Bitcoin order."
        ),
        "captions": [
            "📈 Live Demo 1 (Zero-DOM TradingView Canvas): Locks 4H interval [01],",
            "enables EMA 20/50 Golden Cross [02], sets 1.25 BTC [03], and verifies ORDER FILLED [04]!",
        ],
    },
    {
        "id": "viral_06_mobile",
        "url": "http://127.0.0.1:8501/presentation.html?slide=5&timer=00:21",
        "cached_base": KEYNOTE_CACHE_DIR / "seg_06_base.png",
        "hook_tag": "📱 LIVE DEMO 2: SAMSUNG S25 ULTRA OVER WIRELESS ADB",
        "narration": (
            "Now watch it control a real Samsung S25 Ultra over wireless ADB: disabling alarms and scrolling Instagram Reels hands-free!"
        ),
        "captions": [
            "📱 Live Demo 2 (Physical Samsung S25 Ultra · Wireless ADB · Zero APK):",
            "Muse Voice 1.0 transcribes speech -> disables Sunday alarms -> scrolls Instagram Reels!",
        ],
    },
    {
        "id": "viral_07_heal",
        "url": "http://127.0.0.1:8501/presentation.html?slide=6&timer=00:13",
        "cached_base": KEYNOTE_CACHE_DIR / "seg_07_base.png",
        "hook_tag": "🛡️ AUTONOMOUS SELF-HEALING: 35/35 OBSTRUCTIONS RECOVERED",
        "narration": (
            "When a surprise modal blocks the screen, our verifier detects zero pixel delta, dismisses the blocker, and self-heals!"
        ),
        "captions": [
            "🛡️ Closed-Loop Self-Healing: Detects blocked click (ROI Δ = 0.000), flushes SAM cache,",
            "autonomously dismisses blocker modal [05], and heals 35/35 obstructed runs (100%)!",
        ],
    },
    {
        "id": "viral_08_cta",
        "url": "http://127.0.0.1:8501/presentation.html?slide=7&timer=00:05",
        "cached_base": KEYNOTE_CACHE_DIR / "seg_08_base.png",
        "hook_tag": "🚀 OPEN SOURCE ON GITHUB + 8-TOOL MCP SERVER FOR CURSOR & CLAUDE",
        "narration": (
            "With one hundred percent hit rate and an eight-tool MCP server for Cursor and Claude, MusePilot is open-source on GitHub!"
        ),
        "captions": [
            "🏆 100.0% Hit Rate across 367 Steps · 8-Tool MCP Server for Cursor & Claude Desktop.",
            "⭐ Open-Source on GitHub: github.com/subhajitkp007/MusePilot — Like & Repost!",
        ],
    },
]


def get_audio_duration(audio_path: Path) -> float:
    res = subprocess.run(
        [str(FFMPEG_BIN), "-i", str(audio_path)],
        capture_output=True,
        text=True,
    )
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
    if not m:
        raise RuntimeError(f"Could not parse duration from {audio_path}: {res.stderr}")
    h, mins, secs = int(m.group(1)), int(m.group(2)), float(m.group(3))
    return h * 3600 + mins * 60 + secs


def generate_tts_audio(seg_idx: int, seg: dict, out_mp3: Path) -> float:
    if out_mp3.exists() and out_mp3.stat().st_size > 5000:
        return get_audio_duration(out_mp3)

    if not ELEVENLABS_API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY environment variable is required.")

    prev_text = INDIAN_CONTEXT_PRIMING
    if seg_idx > 0:
        prev_text = INDIAN_CONTEXT_PRIMING + " " + VIRAL_SEGMENTS[seg_idx - 1]["narration"]

    payload = json.dumps(
        {
            "text": seg["narration"],
            "model_id": "eleven_multilingual_v2",
            "previous_text": prev_text,
            "voice_settings": {
                "stability": 0.50,
                "similarity_boost": 0.82,
                "style": 0.22,
                "speed": 1.20,
                "use_speaker_boost": True,
            },
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
        data=payload,
        headers={
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        out_mp3.write_bytes(resp.read())

    return get_audio_duration(out_mp3)


def ensure_base_png(seg: dict, out_png: Path) -> None:
    if out_png.exists() and out_png.stat().st_size > 50000:
        return
    cached = seg.get("cached_base")
    if cached and Path(cached).exists() and Path(cached).stat().st_size > 50000:
        out_png.write_bytes(Path(cached).read_bytes())
        return
    cmd = [
        str(CHROME_BIN),
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        "--window-size=1920,1080",
        "--virtual-time-budget=3200",
        f"--screenshot={out_png}",
        seg["url"],
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial Bold.ttf",
        ]
        if bold
        else [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf",
        ]
    )
    for c in candidates:
        if Path(c).exists():
            try:
                return ImageFont.truetype(c, size=size)
            except Exception:
                pass
    return ImageFont.load_default()


def render_viral_frame(
    base_png: Path,
    hook_tag: str,
    caption_text: str,
    seg_num: int,
    total_segs: int,
    global_progress_pct: float,
    out_png: Path,
) -> None:
    """Render high-retention X/Twitter viral frame with top hook pill and bottom caption bar."""
    base = Image.open(base_png).convert("RGB")
    draw = ImageDraw.Draw(base)

    # Top-center viral hook pill (y=8..44) so autoplay mute viewers are hooked immediately
    font_hook = load_font(15, bold=True)
    bbox = draw.textbbox((0, 0), hook_tag, font=font_hook)
    tw = bbox[2] - bbox[0]
    pill_w = tw + 36
    px1 = (1920 - pill_w) // 2
    px2 = px1 + pill_w
    draw.rounded_rectangle(
        [(px1, 8), (px2, 44)],
        radius=18,
        fill=(8, 20, 44),
        outline=(0, 242, 254),
        width=2,
    )
    draw.text((px1 + 18, 17), hook_tag, fill=(0, 242, 254), font=font_hook)

    # Full-width solid obsidian lower-third caption dock at y=1026..1080
    draw.rectangle([(0, 1026), (1920, 1080)], fill=(3, 7, 18))
    # Glowing cyan/emerald progress bar at y=1022..1026
    draw.rectangle([(0, 1022), (1920, 1026)], fill=(15, 23, 42))
    prog_w = int(1920 * max(0.02, min(1.0, global_progress_pct)))
    draw.rectangle([(0, 1022), (prog_w, 1026)], fill=(0, 242, 254))

    # Left Viral Badge
    draw.rounded_rectangle(
        [(24, 1036), (218, 1070)],
        radius=6,
        fill=(16, 185, 129),
    )
    font_badge = load_font(13, bold=True)
    draw.text((36, 1046), "META AI HACKATHON", fill=(3, 7, 18), font=font_badge)

    # Bold Closed Caption Text (22pt High-Contrast White for X mobile/desktop feed)
    font_cap = load_font(22, bold=True)
    draw.text((238, 1041), caption_text, fill=(255, 255, 255), font=font_cap)

    # Right Scene Counter
    right_text = f"60s LAUNCH CUT · {seg_num:02d}/{total_segs:02d}"
    draw.text((1695, 1046), right_text, fill=(148, 163, 184), font=font_badge)

    base.save(out_png, quality=95)


def format_srt_time(seconds: float) -> str:
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms >= 1000:
        seconds += 1.0
        ms -= 1000
    s = int(seconds) % 60
    m = (int(seconds) // 60) % 60
    h = int(seconds) // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main() -> None:
    print("=" * 72)
    print("🚀 BUILDING MUSEPILOT 60-SECOND VIRAL X LAUNCH VIDEO (1080p)")
    print("=" * 72)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_MP4.parent.mkdir(parents=True, exist_ok=True)

    raw_audio_durations: list[float] = []
    for idx, seg in enumerate(VIRAL_SEGMENTS):
        seg_id = seg["id"]
        base_png = WORK_DIR / f"{seg_id}_base.png"
        raw_mp3 = WORK_DIR / f"{seg_id}_raw.mp3"

        ensure_base_png(seg, base_png)
        dur = generate_tts_audio(idx, seg, raw_mp3)
        raw_audio_durations.append(dur)
        print(f"[{idx+1:02d}/{len(VIRAL_SEGMENTS):02d}] {seg_id}: voice={dur:.2f}s")

    total_raw_voice = sum(raw_audio_durations)
    TARGET_TOTAL_SEC = 60.0
    PAUSE_PER_SEG = 0.25
    total_speech_target = TARGET_TOTAL_SEC - PAUSE_PER_SEG * len(VIRAL_SEGMENTS)
    uniform_tempo = total_raw_voice / total_speech_target
    print(f"✔ Total raw voice: {total_raw_voice:.2f}s -> tempo multiplier: {uniform_tempo:.3f}x")

    final_seg_durations = [
        round((d / uniform_tempo) + PAUSE_PER_SEG, 2) for d in raw_audio_durations
    ]
    diff = round(TARGET_TOTAL_SEC - sum(final_seg_durations), 2)
    final_seg_durations[-1] = round(final_seg_durations[-1] + diff, 2)

    clip_paths: list[Path] = []
    srt_entries: list[str] = []
    srt_counter = 1
    elapsed_sec = 0.0

    for idx, (seg, seg_dur) in enumerate(zip(VIRAL_SEGMENTS, final_seg_durations)):
        seg_id = seg["id"]
        base_png = WORK_DIR / f"{seg_id}_base.png"
        raw_mp3 = WORK_DIR / f"{seg_id}_raw.mp3"
        seg_wav = WORK_DIR / f"{seg_id}_padded.wav"

        if abs(uniform_tempo - 1.0) > 0.01:
            af_filter = f"atempo={uniform_tempo:.4f},apad=whole_dur={seg_dur:.3f}"
        else:
            af_filter = f"apad=whole_dur={seg_dur:.3f}"

        subprocess.run(
            [
                str(FFMPEG_BIN),
                "-y",
                "-i",
                str(raw_mp3),
                "-af",
                af_filter,
                "-ar",
                "44100",
                "-ac",
                "2",
                str(seg_wav),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        captions = seg["captions"]
        char_weights = [max(10, len(c)) for c in captions]
        char_sum = sum(char_weights)
        sub_durs = [round(seg_dur * (cw / char_sum), 2) for cw in char_weights]
        sub_durs[-1] = round(sub_durs[-1] + (seg_dur - sum(sub_durs)), 2)

        img_concat_txt = WORK_DIR / f"{seg_id}_imgs.txt"
        img_concat_lines: list[str] = []
        sub_elapsed = elapsed_sec

        for c_idx, (cap_text, sub_dur) in enumerate(zip(captions, sub_durs)):
            cap_png = WORK_DIR / f"{seg_id}_cap_{c_idx}.png"
            prog_pct = (sub_elapsed + sub_dur * 0.5) / TARGET_TOTAL_SEC
            render_viral_frame(
                base_png=base_png,
                hook_tag=seg["hook_tag"],
                caption_text=cap_text,
                seg_num=idx + 1,
                total_segs=len(VIRAL_SEGMENTS),
                global_progress_pct=prog_pct,
                out_png=cap_png,
            )
            img_concat_lines.append(f"file '{cap_png}'\nduration {sub_dur:.3f}\n")
            if c_idx == len(captions) - 1:
                img_concat_lines.append(f"file '{cap_png}'\n")

            t_start = format_srt_time(sub_elapsed)
            t_end = format_srt_time(sub_elapsed + sub_dur)
            srt_entries.append(f"{srt_counter}\n{t_start} --> {t_end}\n{cap_text}\n")
            srt_counter += 1
            sub_elapsed += sub_dur

        img_concat_txt.write_text("".join(img_concat_lines), encoding="utf-8")

        seg_mp4 = WORK_DIR / f"{seg_id}_clip.mp4"
        subprocess.run(
            [
                str(FFMPEG_BIN),
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(img_concat_txt),
                "-i",
                str(seg_wav),
                "-t",
                f"{seg_dur:.3f}",
                "-vf",
                "fps=30,scale=1920:1080:flags=lanczos,format=yuv420p",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "18",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                str(seg_mp4),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        clip_paths.append(seg_mp4)
        elapsed_sec += seg_dur
        print(f"  ✔ Segment {idx+1:02d}/{len(VIRAL_SEGMENTS):02d}: {seg_dur:.2f}s (Total: {elapsed_sec:.2f}s)")

    OUTPUT_SRT.write_text("\n".join(srt_entries), encoding="utf-8")
    clips_list_txt = WORK_DIR / "viral_clips.txt"
    clips_list_txt.write_text("".join(f"file '{p}'\n" for p in clip_paths), encoding="utf-8")

    subprocess.run(
        [
            str(FFMPEG_BIN),
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(clips_list_txt),
            "-i",
            str(OUTPUT_SRT),
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            "-c:s",
            "mov_text",
            "-metadata:s:s:0",
            "language=eng",
            "-movflags",
            "+faststart",
            str(OUTPUT_MP4),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    WEB_MP4.write_bytes(OUTPUT_MP4.read_bytes())
    final_dur = get_audio_duration(OUTPUT_MP4)
    size_mb = OUTPUT_MP4.stat().st_size / (1024 * 1024)
    print("=" * 72)
    print("🔥 60-SECOND VIRAL X LAUNCH VIDEO READY!")
    print(f"📁 Output Video : {OUTPUT_MP4}")
    print(f"🌐 Web URL      : http://127.0.0.1:8501/assets/musepilot_viral_x_launch.mp4")
    print(f"📝 SRT Captions : {OUTPUT_SRT}")
    print(f"⏱ Duration     : {final_dur:.2f} seconds")
    print(f"📊 File Size    : {size_mb:.2f} MB")
    print("=" * 72)


if __name__ == "__main__":
    main()

