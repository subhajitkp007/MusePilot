# MusePilot — Demo Video & Submission Playbook

> **The 3-Minute Video is the #1 Hackathon Deliverable.**  
> Hackathon judges review hundreds of submissions. Your video must grip them in the first 10 seconds, prove technical depth by 60 seconds, demonstrate live physical mobile/canvas autonomy by 120 seconds, showcase agentic MCP integration by 150 seconds, and leave zero doubt about Meta model integration and open-weight verifier compliance by 180 seconds.

---

## 🎬 1. The 180-Second Winning Screenplay (Timestamp by Timestamp)

```text
  0:00        0:25        0:55        1:35        2:15        2:40        3:00
┌───────────┬───────────┬───────────┬───────────┬───────────┬───────────┬───────┐
│ THE HOOK  │ ZERO-COORD│ DEMO 1    │ DEMO 2    │ DEMO 3    │ META STACK│ CLOSE │
│ Coordinate│ Invariant │ Live Phone│ Canvas &  │ MCP Agent │ 4 Models  │ Call  │
│ Drift Fail│ SAM 3.1   │ ADB Touch │ Self-Heal │ Cursor &  │ Open-Wt   │ to    │
│ Split-Scr │ Step DAG  │ Alarms    │ Replan    │ Claude    │ Baseten   │ Win   │
└───────────┴───────────┴───────────┴───────────┴───────────┴───────────┴───────┘
```

### Shot-by-Shot Screenplay Table

| Timestamp | Story Beat | Visual Presentation on Screen | Exact Voiceover Script | On-Screen Text Callout | Audio / SFX |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **0:00 – 0:25** | **The Crisis: Why Computer-Use Fails in 2026** | **High-Contrast Split Screen:**<br>• *Left Screen (Red Vignette):* Traditional VLM trying to click a button, hallucinating pixel coordinates and missing by 18px due to Retina $2.0\times$ display scaling.<br>• *Right Screen (Electric Cyan):* MusePilot's neon SAM 3.1 Set-of-Mark locking onto the exact sub-pixel boundary with zero coordinates. | *"Autonomous GUI agents routinely fail in production. Why? Because Vision-Language Models hallucinate pixel coordinates—and modern interfaces like HTML5 canvas and mobile apps have zero accessible DOM nodes. A single display scaling difference causes them to click dead air. We solved this with MusePilot."* | `❌ Coordinate Hallucination (Mis-click)`<br>`✅ SAM 3.1 Zero-Coordinate Grounding` | Urgent alarm pulse ➔ clean digital whoosh into cyan |
| **0:25 – 0:55** | **The Core Invariant: Zero-Coordinate DAG** | **Live Enterprise HUD (`http://127.0.0.1:8501`):**<br>• Show the sleek Meta dark-mode Mission Control.<br>• Operator intent: *"Calibrate frequency, damping, and benchmark on canvas."*<br>• SAM 3.1 Set-of-Mark radar lights up with numbered badges (`[01]`, `[02]`, `[03]`).<br>• Dynamic Step Execution DAG animates into view with connected cyan nodes.<br>• Zoom into Pydantic schema validator rejecting raw `[x,y]`. | *"MusePilot enforces a strict architectural invariant: the model is mathematically forbidden from emitting coordinates. Meta's SAM 3.1 segments every interactive control into sub-pixel masks with high-contrast Set-of-Mark badges. Muse Spark then plans over semantic Mask IDs, outputting a verifiable DAG. Touch points are geometrically derived from mask centroids and calibrated for native DPI."* | `Invariant: Zero Raw Coordinates`<br>`Meta SAM 3.1 + Muse Spark DAG`<br>`DPI Calibration (Retina 2.0x • 1.0x)` | Smooth UI chime as Step DAG nodes light up |
| **0:55 – 1:35** | **Demo 1: Cross-App Android Autonomy over Wireless ADB** | **Camera-on-Device Picture-in-Picture (PIP):**<br>• Physical Samsung Galaxy S24 Ultra sitting on desk beside the monitor.<br>• Operator speaks one command: *"Open Clock, turn off all alarms — then open Instagram and play reels."*<br>• Meta Muse Voice Transcribe outputs the live transcript in the HUD.<br>• Phone awakens, opens Clock, switches to the Alarms tab, and toggles off every enabled alarm via calibrated touch.<br>• Cross-app hop: Home → Instagram → Reels tab → video playback starts, one scroll to the next reel.<br>• Every screen transition verified; DAG nodes turn emerald with per-step confidence. | *"Watch MusePilot command a live Samsung Galaxy S24 Ultra over wireless ADB — no on-device software required. From a single spoken command, it opens the Clock, silences every alarm, then jumps to Instagram, opens Reels, and starts playback. Each tap is grounded by SAM 3.1 vision, and Meta's open-weight verifier confirms every screen transition before moving on."* | `📱 Cross-App: Clock ➔ Instagram Reels`<br>`Meta Muse Voice Transcribe`<br>`Every Transition Verified` | Subtle mic beep ➔ authentic phone haptic taps |
| **1:35 – 2:15** | **Demo 2: Opaque HTML5 Canvas & Autonomous Self-Healing** | **Browser + Northbeam Studio console (`demo/canvas_app.html`):**<br>• Open DevTools on the calibration console: nav, sidebar, cards, spectrum chart — yet `0 accessible child nodes`, a single `<canvas>`.<br>• SAM 3.1 overlays (`01`–`04`) lock onto the frequency, damping, gain, and benchmark controls; verified regions turn green.<br>• MusePilot calibrates each control in turn.<br>• **Mid-flight obstruction:** An unexpected system permission modal suddenly pops up blocking the target button!<br>• Verifier detects zero-pixel delta on target; triggers autonomous self-healing branch (Cyber Purple DAG node).<br>• Invalidates SAM 3.1 cache, identifies the modal dismiss mask, clears the blocker, resumes, and verifies goal. | *"Now, the Northbeam calibration console: a realistic product UI with navigation, cards, and charts — rendered as pure pixels with zero accessible DOM nodes. Watch SAM 3.1 lock numbered overlays onto each control while MusePilot calibrates frequency, damping, gain, and the benchmark. But watch what happens when an unexpected system modal pops up mid-run: MusePilot doesn't freeze or crash. It detects the obstruction, invalidates its perceptual cache, triggers an autonomous self-healing replan, dismisses the modal, and verifies the goal."* | `Northbeam Console · 0 DOM Nodes`<br>`Obstruction Detected ➔ Cache Invalidation`<br>`Autonomous Modal Recovery & Replan` | Warning alert tone ➔ purple replan ripple sound |
| **2:15 – 2:40** | **Demo 3: Model Context Protocol (MCP) in Cursor / Claude** | **Cursor / Claude Desktop Split View:**<br>• Developer in Cursor types: *"@musepilot audit the checkout flow on the connected phone."*<br>• Cursor calls MusePilot MCP tool `musepilot_execute_workflow`.<br>• Live HUD flashes with SAM 3.1 radar and Spark execution ledger.<br>• Cursor receives the verified execution trace with 100% centroid hit rate.<br>• Callout: Open-weight verifier `meta-models/muse-spark-open-1026` hosted on Baseten. | *"We didn't just build a dashboard—we turned MusePilot into open agent infrastructure with the Model Context Protocol. Any AI assistant—Cursor, Claude Desktop, or Antigravity—can invoke MusePilot as an MCP tool to automate and test real software. Under the hood, verification is powered by Meta's open-weight Muse Spark Open running on Baseten."* | `🤖 Open Model Context Protocol (MCP)`<br>`Works with Cursor, Claude, Antigravity`<br>`Meta Open-Weight: muse-spark-open-1026 on Baseten` | Keyboard click ➔ MCP tool execution chime |
| **2:40 – 3:00** | **The Winning Close: Production Ready** | **Metrics Intelligence Tab & GitHub Repo:**<br>• Executive Metrics Tab: 100% Mask Centroid Hit Rate, 0% Coordinate Drift, 135/135 tests passing.<br>• Enterprise JWT session security & sliding-window rate limiting.<br>• Clean GitHub repository URL (`github.com/subhajitkp007/MusePilot`).<br>• Decisive closing statement. | *"Zero coordinates. 100% verified. Autonomous self-healing across mobile, desktop, canvas, and MCP agents. Built on Meta's multimodal foundation with 135 passing tests and enterprise security. Welcome to the future of reliable computer use with MusePilot."* | `🏆 Track: Push the Frontier ($400,000 Pool)`<br>`⭐ $10K Open-Weight Bonus Verified`<br>`135 Tests Passing • Apache 2.0 Open Source` | Triumphant crescendo with clean fadeout |

---

## 🎙️ 2. Word-for-Word Voiceover Script (Teleprompter Ready)

```text
[0:00 - THE HOOK]
"Autonomous GUI agents routinely fail in production. Why? Because Vision-Language 
Models hallucinate pixel coordinates—and modern interfaces like HTML5 canvas and 
mobile apps have zero accessible DOM nodes. A single display scaling difference 
causes them to click dead air. We solved this with MusePilot."

[0:25 - THE BREAKTHROUGH]
"MusePilot enforces a strict architectural invariant: the model is mathematically 
forbidden from emitting coordinates. Meta's SAM 3.1 segments every interactive control 
into sub-pixel masks with high-contrast Set-of-Mark badges. Muse Spark then plans 
over semantic Mask IDs, outputting a verifiable DAG. Touch points are geometrically 
derived from mask centroids and calibrated for native DPI."

[0:55 - DEMO 1: CROSS-APP ANDROID (CLOCK + INSTAGRAM REELS)]
"Watch MusePilot command a live Samsung Galaxy S24 Ultra over wireless ADB — no 
on-device software required. From a single spoken command, it opens the Clock, 
silences every alarm, then jumps to Instagram, opens Reels, and starts playback. 
Each tap is grounded by SAM 3.1 vision, and Meta's open-weight verifier confirms 
every screen transition before moving on."

[1:35 - DEMO 2: CANVAS & SELF-HEALING]
"Now, the Northbeam calibration console: a realistic product UI with navigation, 
cards, and charts — rendered as pure pixels with zero accessible DOM nodes. Watch 
SAM 3.1 lock numbered overlays onto each control while MusePilot calibrates frequency, 
damping, gain, and the benchmark. But watch what happens when an unexpected system 
modal pops up mid-run: MusePilot doesn't freeze or crash. It detects the obstruction, 
invalidates its perceptual cache, triggers an autonomous self-healing replan, 
dismisses the modal, and verifies the goal."

[2:15 - DEMO 3: MCP AGENT INFRASTRUCTURE]
"We didn't just build a dashboard—we turned MusePilot into open agent infrastructure 
with the Model Context Protocol. Any AI assistant—Cursor, Claude Desktop, or 
Antigravity—can invoke MusePilot as an MCP tool to automate and test real software. 
Under the hood, verification is powered by Meta's open-weight Muse Spark Open 
running on Baseten."

[2:40 - THE WINNING CLOSE]
"Zero coordinates. 100% verified. Autonomous self-healing across mobile, desktop, 
canvas, and MCP agents. Built on Meta's multimodal foundation with 135 passing tests 
and enterprise security. Welcome to the future of reliable computer use with MusePilot."
```

---

## 🏆 3. Why This Video Secures the Grand Prize ($185,000 Total Stack)

This video directly addresses every criterion on the Cerebral Valley / Meta judge scorecards:

1. **Track Alignment: Push the Frontier ($150,000 Grand Prize):**
   - Proven autonomous actuation over physical Android hardware and opaque zero-DOM WebGL canvases.
   - Solves coordinate drift—the single biggest barrier preventing VLMs from controlling computers.
2. **Best Build on Meta Open Weight Models ($10,000 Bonus):**
   - Explicit visual callout of `meta-models/muse-spark-open-1026` hosted on Baseten partner inference performing closed-loop visual state verification on every step.
3. **Best Agentic Use-Case ($5,000 Bonus):**
   - Shows genuine autonomy: multi-step DAG planning, transient modal obstruction detection, cache invalidation, and dynamic self-healing replanning without human intervention.
4. **Model Context Protocol (MCP) Ecosystem Multiplier:**
   - Demonstrating Cursor and Claude Desktop invoking MusePilot proves it is extensible developer infrastructure, not a throwaway prototype.
5. **Most Viral Project ($20,000 Bonus):**
   - The opening 10-second split-screen hook and the physical Samsung S24 Ultra actuation are tailor-made for viral reach on X.

---

## 🛠️ 4. Recording & Production Checklist

1. **Screen Layout (1920×1080 @ 60 FPS):**
   - Fullscreen browser at `http://127.0.0.1:8501/` with browser UI hidden (`F11` or full screen).
   - Zoom level at 90% so all panels (Step DAG, Set-of-Mark radar, and Ledger) fit cleanly.
2. **Camera Picture-in-Picture Setup:**
   - Phone mounted on desk stand visible in bottom-right corner during Demo 1.
   - Hands visibly away from the phone to prove autonomous wireless ADB execution.
3. **Audio Quality:**
   - Crisp voiceover using a condenser microphone with noise suppression applied.
   - Pacing: **140 to 150 words per minute** (confident, articulate, no filler words).
4. **Captions:**
   - High-contrast animated burned-in subtitles (over 70% of judges watch videos on low volume).
5. **Fail-Safe Fallback:**
   - If Wi-Fi or API gateway latency spikes while recording, use the built-in deterministic replayer:
     ```bash
     .venv/bin/python -m musepilot replay demo/traces/w1_golden_trace.json
     .venv/bin/python -m musepilot replay demo/traces/w2_golden_trace.json
     ```

---

## 📋 5. Submission Copy & Form Fields

- **Project Title:** `MusePilot: Zero-Coordinate, Visually-Verified Multimodal GUI Agent`
- **Tagline:** `Autonomous visual automation across Android ADB, Desktop, and Canvas with Meta SAM 3.1, Muse Spark, Muse Spark Open, and MCP.`
- **Track:** `Push the Frontier (Indie Developer)`
- **Bonus Categories Selected:**
  - `Best Build on Meta Open Weight Models` (`meta-models/muse-spark-open-1026` on Baseten)
  - `Best Agentic Use-Case`
  - `Most Viral Project`
- **Repository URL:** `https://github.com/subhajitkp007/MusePilot`
- **Video Link:** *YouTube Unlisted / Loom Link (Verified in Incognito)*


---

## 🛠️ 2. Production & Recording Best Practices

### Video Quality & Audio Setup
1. **Resolution & Aspect Ratio:**
   - Record at **1080p (1920×1080)** or **1440p (2560×1440)** at 60fps.
   - Set browser zoom to **90% or 100%** so the HUD, Step DAG, and Visual Grounding Radar fit on screen without vertical scrolling.
2. **Audio & Microphone:**
   - Use a dedicated USB condenser microphone (Blue Yeti, Shure, or Rode).
   - Apply clean noise suppression using Audacity, Descript, or OBS Noise Gate.
   - Maintain an upbeat, confident, and articulate presentation cadence.
3. **Picture-in-Picture Setup for Live Mobile Demo:**
   - Set up your webcam or smartphone on a tripod pointing at the physical Android phone sitting next to your keyboard.
   - Show your hand away from the screen while MusePilot executes the touch event over ADB to prove genuine autonomous control.
4. **Closed Captions (Mandatory for Social Reach):**
   - Burn in animated high-contrast closed captions using CapCut, Premiere Pro, or Descript. Over **75% of social media reviewers and judges** watch videos initially on mute or low volume.

---

## ⚡ 3. Fail-Safe Live Demo Protocol (Zero-Risk Rehearsal)

If network conditions or live model inference latencies spike during video recording or live finals evaluation, utilize MusePilot's built-in **Deterministic Trace Replayer**:

```bash
# 1. Verify system readiness, ADB connectivity, and DPI calibration
python -m musepilot.health

# 2. Execute live ADB Android run (Samsung Galaxy S24 Ultra)
python -m musepilot.cli run --driver adb --workflow w2 --intent "Open Clock and set alarm for 9 AM"

# 3. Deterministic Fallback: Replay golden traces with zero network dependency
python -m musepilot.cli replay demo/traces/w1_golden_trace.json
python -m musepilot.cli replay demo/traces/w2_golden_trace.json
```

---

## 📋 4. Cerebral Valley Submission Checklist (Nov 4, 9:00 PM ET)

> [!IMPORTANT]
> **Self-Imposed Target:** Submit by **6:00 PM ET on November 4** (3 hours ahead of the official deadline) to protect against server congestion.

- [ ] **Track Selection:**
  - **Push the Frontier** (Indie Developer Track • $400,000 Pool).
- [ ] **Bonus Category Declarations:**
  - **Best Build on Meta Open Weight Models ($10,000):** Explicitly highlight `meta-models/muse-spark-open-1026` hosted on Baseten.
  - **Best Agentic Use-Case ($5,000):** Detail the autonomous closed-loop planning, execution, and modal self-healing recovery.
  - **Most Viral Project ($20,000):** Post high-energy teaser clip on X by Nov 5 morning.
- [ ] **Public GitHub Repository:**
  - Visibility: **Public** (`https://github.com/subhajitkp007/MusePilot`).
  - Apache-2.0 License in root.
  - Comprehensive README with Mermaid architecture diagram and 5 production use cases.
  - Commit history active across the hackathon window (Oct 27 – Nov 4, 2026).
- [ ] **3-Minute Video Link:**
  - YouTube (Unlisted or Public) or Loom link.
  - **Verified in an Incognito / Private browser tab** without signing in.

---

## 🚀 5. Viral Launch Playbook (Winning the $20,000 Most Viral Prize)

The **Most Viral Project** bonus awards **$20,000** for the submission with the highest organic engagement on X (formerly Twitter) between submission and **November 8 EOD**.

### Launch Strategy (Post on X by Nov 5 at 9:00 AM ET):
1. **The Native Video Hook (45-Second Cut):**
   - Post a high-energy 45-second teaser directly uploaded as native media (native X video receives $10\times$ higher algorithmic impressions than external links).
   - Hook: Split-screen of traditional coordinate agent clicking air vs. MusePilot locking on with a neon SAM 3.1 mask + live Android phone actuation.
2. **Tweet Copy Template:**
   ```text
   We just solved the biggest failure mode in autonomous computer use: coordinate hallucination.

   Introducing MusePilot: the first zero-coordinate, visually-verified GUI agent powered by Meta’s SAM 3.1 & Muse models.

   Watch it control an inaccessible HTML5 canvas AND a live Samsung phone over ADB with 100% verified accuracy 🧵👇
   ```
3. **The Thread Structure:**
   - **Tweet 1:** Hook + 45s high-energy native video.
   - **Tweet 2:** The Zero-Coordinate Invariant (Why predicting coordinates fails and how SAM 3.1 Set-of-Mark math fixes it).
   - **Tweet 3:** Autonomous Self-Healing (How Muse Spark Open 1026 detects blocking modals and dismisses them automatically).
   - **Tweet 4:** Live mobile automation over wireless ADB with 1:1 physical pixel accuracy.
   - **Tweet 5:** Links to the 3-minute full demo video, GitHub repo, and Cerebral Valley project page.
   - **Tweet 6:** Mentions & acknowledgments: `@CerebralValley`, `@MetaAI`, `@basetenco`, and key AI researchers.
4. **Community Engagement:**
   - Reply to all technical questions and comments within 15 minutes of posting during the first 6 hours.
   - Engage the Cerebral Valley community gallery during public voting.
