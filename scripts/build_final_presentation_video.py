#!/usr/bin/env python3
"""
scripts/build_final_presentation_video.py
=========================================
Builds the 3-Minute (180.0s) 1920x1080 Fullscreen Keynote Presentation Video
for the Meta Global AI Hackathon 2026 featuring:
  1. 14 Fullscreen 1920x1080 Keynote + Interactive Sandbox Modal Visual Segments
  2. ElevenLabs Multilingual v2 Voiceover (Indian IT Principal Architect persona)
  3. Synchronized Broadcast Lower-Third Closed Captions burned into the bottom dock
     + standard .srt subtitle track embedded in the MP4 container
  4. Exact 180.0-second (03:00) total runtime in 1080p H.264 + AAC with ZERO audio cutoff
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
import urllib.request
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FFMPEG_BIN = (
    PROJECT_ROOT
    / ".venv/lib/python3.14/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1"
)
CHROME_BIN = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
WORK_DIR = Path(
    "/Users/subhajitmahata/.gemini/antigravity/brain/9e06e823-7295-4596-9c21-ee4f8ce611eb/scratch/video_build_v2"
)
OUTPUT_MP4 = PROJECT_ROOT / "demo/musepilot_final_presentation_3min.mp4"
OUTPUT_SRT = PROJECT_ROOT / "demo/musepilot_final_presentation_3min.srt"
WEB_MP4 = PROJECT_ROOT / "musepilot/server/static/web/assets/musepilot_final_presentation_3min.mp4"

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
VOICE_ID = "onwK4e9ZLuTAKqWW03F9"
INDIAN_CONTEXT_PRIMING = (
    "Namaste judges! Myself Subhajit Mahata, Principal AI Architect from Bengaluru, India."
)

# 14 Tight, High-Impact Keynote Segments (Paced for 180.0s with zero truncation)
SEGMENTS = [
    {
        "id": "seg_01a",
        "url": "http://127.0.0.1:8501/presentation.html?slide=0&timer=03:00",
        "target_duration": 10.5,
        "narration": (
            "Namaste judges! Welcome to MusePilot: the zero-coordinate multimodal GUI agent "
            "built for the Meta Global AI Hackathon 2026."
        ),
        "captions": [
            "Namaste Judges! Welcome to MusePilot — Meta Global AI Hackathon 2026.",
            "The world's first Zero-Coordinate Multimodal GUI Agent.",
        ],
    },
    {
        "id": "seg_01b",
        "url": "http://127.0.0.1:8501/presentation.html?slide=0&view=workspace&timer=02:50",
        "target_duration": 10.5,
        "narration": (
            "Instead of guessing fragile pixel coordinates, MusePilot unifies four native Meta AI models "
            "to achieve a one hundred percent centroid hit rate."
        ),
        "captions": [
            "Eliminates fragile [x, y] pixel guessing across Android, WebGL, and IDEs,",
            "unifying 4 native Meta AI models with a 100.0% SAM centroid hit rate.",
        ],
    },
    {
        "id": "seg_02a",
        "url": "http://127.0.0.1:8501/presentation.html?slide=1&scenario=retina&timer=02:39",
        "target_duration": 9.0,
        "narration": (
            "Why do traditional GUI agents fail in production? On Retina two-X displays, "
            "raw coordinate guesses drift by twenty-four pixels and mis-click."
        ),
        "captions": [
            "Why traditional GUI agents fail: On Retina 2.0× displays, raw [x, y] guesses",
            "drift by 18–30 pixels—missing buttons and clicking dead background.",
        ],
    },
    {
        "id": "seg_02b",
        "url": "http://127.0.0.1:8501/presentation.html?slide=1&scenario=canvas&timer=02:30",
        "target_duration": 9.0,
        "narration": (
            "Second, on zero-DOM WebGL canvases like TradingView, Playwright and Selenium crash "
            "because there are zero accessible DOM nodes."
        ),
        "captions": [
            "Second, on zero-DOM WebGL canvases like TradingView Pro,",
            "Playwright and Selenium crash 100% of the time due to 0 DOM child nodes.",
        ],
    },
    {
        "id": "seg_02c",
        "url": "http://127.0.0.1:8501/presentation.html?slide=1&scenario=android&timer=02:21",
        "target_duration": 9.5,
        "narration": (
            "And third, on physical Android hardware over wireless ADB, MusePilot maps "
            "Meta SAM 3.1 mask centroids one-to-one with zero pixel drift."
        ),
        "captions": [
            "Third, on physical Android hardware over Wireless ADB, MusePilot maps",
            "Meta SAM 3.1 mask polygons 1:1 to calibrated touch points with 0.0px drift.",
        ],
    },
    {
        "id": "seg_03",
        "url": "http://127.0.0.1:8501/presentation.html?slide=2&timer=02:11",
        "target_duration": 16.0,
        "narration": (
            "Here is our production schema boundary in schemas dot py. Our Pydantic validator strictly forbids "
            "raw coordinate keys like X, Y, or B-Box. Muse Spark plans exclusively over symbolic target mask IDs "
            "from Meta SAM 3.1."
        ),
        "captions": [
            "Core Architecture (musepilot/contracts/schemas.py): Pydantic validator strictly",
            "forbids raw [x, y] keys—enforcing the Zero-Coordinate Invariant in code.",
            "Muse Spark 1.3 plans exclusively over symbolic SAM 3.1 target_mask_id integers.",
        ],
    },
    {
        "id": "seg_04",
        "url": "http://127.0.0.1:8501/presentation.html?slide=3&timer=01:55",
        "target_duration": 17.5,
        "narration": (
            "We integrate four native Meta models: SAM 3.1 for segmentation, Muse Spark 1.3 for planning, "
            "Muse Voice for speech intake, and for the ten-thousand-dollar Open-Weights track, "
            "Muse Spark Open hosted on Baseten verifies every ROI pixel transition."
        ),
        "captions": [
            "Full-Stack Meta AI Loop: SAM 3.1 + Muse Spark 1.3 + Muse Voice Transcribe 1.0.",
            "For the $10,000 Meta Open-Weights Track, meta-models/muse-spark-open-1026 on Baseten",
            "gates every action via dual ROI pixel-delta (≥1.5%) and visual state verification.",
        ],
    },
    {
        "id": "seg_05a",
        "url": "http://127.0.0.1:8501/presentation.html?slide=4&timer=01:38",
        "target_duration": 11.5,
        "narration": (
            "In Core Example One, MusePilot operates a live TradingView Pro WebGL canvas. "
            "Where DOM selectors see zero nodes, SAM 3.1 segments the chart into masks one through four."
        ),
        "captions": [
            "Core Example 1 (Zero-DOM WebGL Canvas): Autonomous TradingView Pro Terminal.",
            "Where DOM inspect yields 0 nodes, SAM 3.1 segments masks [01]–[04] directly from pixels.",
        ],
    },
    {
        "id": "seg_05b",
        "url": "http://127.0.0.1:8501/presentation.html?slide=4&modal=tradingview&timer=01:26",
        "target_duration": 13.0,
        "narration": (
            "Inside our live interactive terminal, the agent locks the four-hour interval, enables the EMA Golden Cross, "
            "sets one-point-two-five Bitcoin size, and verifies the live buy order fill."
        ),
        "captions": [
            "Live In-Slide Sandbox: MusePilot locks the 4H interval [01], enables EMA 20/50 [02],",
            "sets 1.25 BTC limit size [03], and verifies ORDER FILLED [04] via Baseten.",
        ],
    },
    {
        "id": "seg_06",
        "url": "http://127.0.0.1:8501/presentation.html?slide=5&timer=01:13",
        "target_duration": 17.5,
        "narration": (
            "In Core Example Two, MusePilot controls a physical Samsung Galaxy S24 Ultra over wireless ADB with zero APK installed. "
            "From one spoken command via Muse Voice, it opens Clock, disables Sunday alarms, and launches Instagram Reels."
        ),
        "captions": [
            "Core Example 2 (Physical Samsung Galaxy S24 Ultra over Wireless ADB · Zero APK):",
            "Muse Voice 1.0 transcribes: 'Open Clock, turn off Sunday alarms, then play Instagram Reels.'",
            "AdbDeviceDriver streams 1080×2340 frames and dispatches 1:1 calibrated touch taps.",
        ],
    },
    {
        "id": "seg_07",
        "url": "http://127.0.0.1:8501/presentation.html?slide=6&timer=00:56",
        "target_duration": 17.5,
        "narration": (
            "For the five-thousand-dollar Best Agentic Use-Case track, watch our self-healing state machine. "
            "When a system modal blocks target mask two, our verifier detects zero pixel delta, flushes the SAM cache, "
            "dismisses mask five, and heals thirty-five out of thirty-five trials."
        ),
        "captions": [
            "Best Agentic Use-Case ($5K Track): Autonomous Self-Healing State Machine.",
            "Detects blocked click (ROI Δ = 0.000), flushes SHA-256 SAM cache, splices recovery",
            "node to dismiss modal [05], and resumes original goal—35/35 obstructions healed (100%).",
        ],
    },
    {
        "id": "seg_08",
        "url": "http://127.0.0.1:8501/presentation.html?slide=7&timer=00:38",
        "target_duration": 13.5,
        "narration": (
            "Through our official Model Context Protocol server, we expose eight native tools over stdio and SSE, "
            "giving Cursor, Claude Desktop, and Antigravity instant SAM 3.1 vision and hardware control."
        ),
        "captions": [
            "Ecosystem Multiplier: Official 8-Tool Model Context Protocol (MCP) Server.",
            "Exposes SAM 3.1 segmentation, Muse Spark planning, and ADB actuation to Cursor & Claude.",
        ],
    },
    {
        "id": "seg_09",
        "url": "http://127.0.0.1:8501/presentation.html?slide=8&timer=00:25",
        "target_duration": 13.0,
        "narration": (
            "Across ninety empirical runs and three hundred sixty-seven steps, we achieved one hundred percent hit rate, "
            "backed by one hundred fifty-seven passing tests, W3C OpenTelemetry tracing, and JWT security."
        ),
        "captions": [
            "Production Engineering: 100.0% Hit Rate across 90 Runs / 367 Steps & 35/35 Self-Heals.",
            "Backed by 157/157 passing automated tests, W3C OpenTelemetry spans, and JWT security.",
        ],
    },
    {
        "id": "seg_10",
        "url": "http://127.0.0.1:8501/presentation.html?slide=9&timer=00:12",
        "target_duration": 12.0,
        "narration": (
            "Four native Meta AI models, a zero-coordinate invariant, live WebGL and wireless Android autonomy, "
            "and Baseten open-weight verification. Thank you, judges—MusePilot is ready to win."
        ),
        "captions": [
            "Grand Prize Scorecard: 4 Native Meta Models · Zero-Coordinate Invariant · Baseten Verifier.",
            "Thank you, Judges! MusePilot — Pushing the Frontier at Meta Global AI Hackathon 2026.",
        ],
    },
]


def get_audio_duration(audio_path: Path) -> float:
    """Measure exact duration in seconds using FFmpeg."""
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
    """Generate ElevenLabs voiceover for a segment with Indian IT professional priming."""
    if out_mp3.exists() and out_mp3.stat().st_size > 5000:
        return get_audio_duration(out_mp3)

    prev_text = INDIAN_CONTEXT_PRIMING
    if seg_idx > 0:
        prev_text = INDIAN_CONTEXT_PRIMING + " " + SEGMENTS[seg_idx - 1]["narration"]

    payload = json.dumps(
        {
            "text": seg["narration"],
            "model_id": "eleven_multilingual_v2",
            "previous_text": prev_text,
            "voice_settings": {
                "stability": 0.55,
                "similarity_boost": 0.80,
                "style": 0.16,
                "speed": 1.18,
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
        audio_bytes = resp.read()
        out_mp3.write_bytes(audio_bytes)

    return get_audio_duration(out_mp3)


def capture_fullscreen_png(url: str, out_png: Path) -> None:
    """Capture a 1920x1080 edge-to-edge fullscreen frame via headless Chrome."""
    if out_png.exists() and out_png.stat().st_size > 50000:
        return
    cmd = [
        str(CHROME_BIN),
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        "--window-size=1920,1080",
        "--virtual-time-budget=3200",
        f"--screenshot={out_png}",
        url,
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


def render_captioned_frame(
    base_png: Path,
    caption_text: str,
    seg_num: int,
    total_segs: int,
    global_progress_pct: float,
    out_png: Path,
) -> None:
    """
    Burn a 100% opaque broadcast lower-third closed-caption dock at the bottom of the
    1920x1080 fullscreen slide (y = 1030..1080) so zero underlying text bleeds through.
    """
    base = Image.open(base_png).convert("RGB")
    draw = ImageDraw.Draw(base)

    # Full-width solid obsidian lower-third caption dock at y=1032..1080
    draw.rectangle([(0, 1032), (1920, 1080)], fill=(3, 7, 18))
    # Glowing cyan progress bar at y=1029..1032
    draw.rectangle([(0, 1029), (1920, 1032)], fill=(15, 23, 42))
    prog_w = int(1920 * max(0.02, min(1.0, global_progress_pct)))
    draw.rectangle([(0, 1029), (prog_w, 1032)], fill=(0, 242, 254))

    # Left CC Live Narration Badge (Solid dark-cyan fill so nothing bleeds through)
    badge_x1, badge_y1, badge_x2, badge_y2 = 24, 1040, 202, 1072
    draw.rounded_rectangle(
        [(badge_x1, badge_y1), (badge_x2, badge_y2)],
        radius=6,
        fill=(6, 32, 54),
        outline=(0, 242, 254),
        width=1,
    )
    font_badge = load_font(13, bold=True)
    draw.text((38, 1049), "CC · LIVE AUDIO", fill=(0, 242, 254), font=font_badge)

    # Center-left Closed Caption Text (High-Contrast White)
    font_cap = load_font(20, bold=True)
    draw.text((222, 1045), caption_text, fill=(248, 250, 252), font=font_cap)

    # Right Scene Counter Pill
    right_text = f"MUSEPILOT KEYNOTE · PART {seg_num:02d}/{total_segs:02d}"
    draw.text((1640, 1049), right_text, fill=(148, 163, 184), font=font_badge)

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
    print("🎬 BUILDING MUSEPILOT 3-MINUTE (180s) FULLSCREEN CAPTIONED KEYNOTE VIDEO")
    print("=" * 72)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_MP4.parent.mkdir(parents=True, exist_ok=True)

    # Step 1: Capture all 14 fullscreen 1920x1080 base PNGs and generate ElevenLabs TTS
    raw_audio_durations: list[float] = []
    for idx, seg in enumerate(SEGMENTS):
        seg_id = seg["id"]
        base_png = WORK_DIR / f"{seg_id}_base.png"
        raw_mp3 = WORK_DIR / f"{seg_id}_raw.mp3"

        print(f"[{idx+1:02d}/{len(SEGMENTS):02d}] Capturing 1920x1080 fullscreen slide: {seg['url']}")
        capture_fullscreen_png(seg["url"], base_png)

        print(f"[{idx+1:02d}/{len(SEGMENTS):02d}] Generating ElevenLabs voiceover ({seg_id})...")
        dur = generate_tts_audio(idx, seg, raw_mp3)
        raw_audio_durations.append(dur)
        print(f"    -> Raw voice duration: {dur:.2f}s")

    total_raw_voice = sum(raw_audio_durations)
    print(f"\n✔ Total raw ElevenLabs speech duration: {total_raw_voice:.2f}s")

    # Step 2: Compute uniform tempo & per-segment duration so:
    #   - Every single word finishes with a 0.45s breath pause before slide change (0% cutoff!)
    #   - Total duration across all 14 segments == 180.00 seconds (3:00)
    TARGET_TOTAL_SEC = 180.0
    PAUSE_PER_SEG = 0.45
    total_speech_target = TARGET_TOTAL_SEC - PAUSE_PER_SEG * len(SEGMENTS)
    uniform_tempo = total_raw_voice / total_speech_target
    print(f"✔ Uniform speech tempo multiplier: {uniform_tempo:.3f}x (100% uncut speech + {PAUSE_PER_SEG}s pauses)")

    final_seg_durations = [
        round((d / uniform_tempo) + PAUSE_PER_SEG, 2) for d in raw_audio_durations
    ]
    diff = round(TARGET_TOTAL_SEC - sum(final_seg_durations), 2)
    final_seg_durations[-1] = round(final_seg_durations[-1] + diff, 2)
    print(f"✔ Calibrated total video duration: {sum(final_seg_durations):.2f}s (Exactly 3:00)")

    # Step 3: Build padded/tempo-matched audio and captioned sub-clips for each segment
    clip_paths: list[Path] = []
    srt_entries: list[str] = []
    srt_counter = 1
    elapsed_sec = 0.0

    for idx, (seg, raw_dur, seg_dur) in enumerate(
        zip(SEGMENTS, raw_audio_durations, final_seg_durations)
    ):
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

        # Split segment duration across its caption lines proportional to character length
        captions = seg["captions"]
        char_weights = [max(10, len(c)) for c in captions]
        char_sum = sum(char_weights)
        sub_durs = [
            round(seg_dur * (cw / char_sum), 2) for cw in char_weights
        ]
        sub_durs[-1] = round(sub_durs[-1] + (seg_dur - sum(sub_durs)), 2)

        img_concat_txt = WORK_DIR / f"{seg_id}_imgs.txt"
        img_concat_lines: list[str] = []
        sub_elapsed = elapsed_sec

        for c_idx, (cap_text, sub_dur) in enumerate(zip(captions, sub_durs)):
            cap_png = WORK_DIR / f"{seg_id}_cap_{c_idx}.png"
            prog_pct = (sub_elapsed + sub_dur * 0.5) / TARGET_TOTAL_SEC
            render_captioned_frame(
                base_png=base_png,
                caption_text=cap_text,
                seg_num=idx + 1,
                total_segs=len(SEGMENTS),
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
        print(
            f"  ✔ Built segment {idx+1:02d}/{len(SEGMENTS):02d} ({seg_id}): {seg_dur:.2f}s (Cumulative: {elapsed_sec:.2f}s)"
        )

    OUTPUT_SRT.write_text("\n".join(srt_entries), encoding="utf-8")
    print(f"\n✔ Wrote synchronized SRT subtitle track: {OUTPUT_SRT}")

    clips_list_txt = WORK_DIR / "all_clips.txt"
    clips_list_txt.write_text(
        "".join(f"file '{p}'\n" for p in clip_paths), encoding="utf-8"
    )

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
    print("🏆 FINAL 3-MINUTE FULLSCREEN CAPTIONED PRESENTATION VIDEO READY!")
    print(f"📁 Output Video : {OUTPUT_MP4}")
    print(f"🌐 Web URL      : http://127.0.0.1:8501/assets/musepilot_final_presentation_3min.mp4")
    print(f"📝 SRT Captions : {OUTPUT_SRT}")
    print(f"⏱ Duration     : {final_dur:.2f} seconds ({final_dur/60:.2f} minutes)")
    print(f"📊 File Size    : {size_mb:.2f} MB (1920x1080 Full HD H.264 + AAC)")
    print("=" * 72)


if __name__ == "__main__":
    main()
