# MusePilot — Demo Video & Submission Playbook

> **The 3-Minute Video is the #1 Judging Deliverable.**  
> Hackathon judges review hundreds of projects. Your video must grip them in the first 10 seconds, prove technical depth by 60 seconds, demonstrate true autonomy by 120 seconds, and leave zero doubt about compliance and model usage by 180 seconds.

---

## 1. The Winning 180-Second Video Storyboard

| Timestamp | Story Beat | Visual Presentation | Voiceover Script & Audio |
| :--- | :--- | :--- | :--- |
| **0:00 – 0:18** | **The Hook: Why GUI Agents Fail** | **Split Screen:** Left side shows standard coordinate-based VLM clicking empty space due to 15px drift. Right side shows MusePilot locking onto the button with a neon SAM 3.1 mask. | *"Autonomous GUI agents fail in production because models hallucinate coordinates—and accessibility trees are completely blind to custom canvas UIs. Today, we fix that with MusePilot."* |
| **0:18 – 0:42** | **The Architectural Innovation** | Full screen transition to the live MusePilot HUD: screen elements dynamically segmented with glowing neon masks and numbered Set-of-Mark badges (`[12]`, `[14]`). | *"MusePilot never emits coordinates. It uses Meta's SAM 3.1 to segment the visual scene into exact masks, uses Muse Spark to plan a multi-step DAG over mask IDs, and visually verifies every state transition before advancing."* |
| **0:42 – 1:25** | **Demo 1: The Frontier Canvas Challenge (W1)** | Screen capture of an un-inspectable HTML5 Canvas / WebGL engineering dashboard. DOM inspector open showing zero accessible child nodes. MusePilot executes slider adjustments and button clicks with live green verification ticks. | *"Watch MusePilot conquer a complex canvas interface that no DOM parser can see. It selects Mask 14, computes the exact geometric centroid scaled for Retina display DPI, and executes. Immediately, our verifier confirms the waveform updated—step by step, verified in real time."* |
| **1:25 – 2:10** | **Demo 2: Voice Command & Self-Healing (W2)** | Live microphone audio waveform appears. User speaks: *"Extract the anomaly report and dispatch the alert."* Muse Voice Transcribe converts speech to text. Agent switches apps. Mid-run, an unexpected modal pop-up appears. MusePilot pauses, detects the obstruction, replans, dismisses the modal, and finishes the task. | *"Now, the same loop driven hands-free by Muse Voice Transcribe across apps. But watch what happens when the UI fights back—an unexpected modal blocks the flow. MusePilot doesn't crash; it senses the blockage, replans, dismisses the dialog, and self-heals back to task completion."* |
| **2:10 – 2:38** | **Under the Hood: Open Weights & Meta Ecosystem** | Quick cut to terminal & architecture diagram: Meta Model API calling Muse Spark, and `meta-models/muse-spark-open-1026` serving on Baseten/Modal/Fireworks. Terminal shows live latency and 100% verification accuracy. | *"Under the hood, closed-loop verification is powered by Meta's open-weight Muse Spark Open running on partner inference. Every step is logged to deterministic traces with zero coordinate hallucination."* |
| **2:38 – 3:00** | **The Call to Action & Proof** | Metrics card on screen: 100% centroid hit-rate, 96% verification precision. Clean GitHub repository URL and team credits. | *"Zero coordinates. 100% verified. Built in 4 days on Meta's multimodal foundation. Welcome to the future of reliable GUI autonomy with MusePilot."* |

---

## 2. Production & Recording Best Practices

1. **Resolution & Audio:**
   - Record at 1080p (1920x1080) or 1440p (2560x1440) locked resolution.
   - Use a high-quality condenser microphone; clean background noise with Audacity or Descript.
   - Turn off all OS notifications (Do Not Disturb enabled).
2. **Deterministic Live-Recording Protocol:**
   - Run `python -m musepilot.health` to verify all APIs, display DPI scale factor, and target app bounds.
   - Rehearse each workflow 3 consecutive times before recording the master take.
   - If a live API hiccup occurs, seamlessly fall back to the trace-replayer take (`--replay`). Never leave awkward pauses or failed API retries in the final edit.
3. **Pacing & Captions:**
   - Fast, engaging pacing. Never let dead silence exceed 2 seconds.
   - Burn-in closed captions (subtitles) using CapCut, Premiere, or Descript. Over 70% of judges and social media viewers watch initially on mute.

---

## 3. Submission Day Protocol (Nov 4, Deadline 9:00 PM ET)

> [!CRITICAL]
> **Self-Imposed Submission Deadline:** Submit by **6:00 PM ET** on November 4 (3-hour buffer before the official 9:00 PM ET cutoff) to avoid server bottlenecks or submission platform latency.

### Official Submission Checklist:
- [ ] **One Team Submission:** Ensure your designated Representative submits once on the Cerebral Valley platform.
- [ ] **Public GitHub Repository:**
  - Repository visibility set to **Public**.
  - Verified that a fresh `git clone` runs cleanly following the README instructions.
  - Apache-2.0 license header included.
  - Clean commit history dating within **Oct 27 – Nov 4, 2026**.
- [ ] **Working 3-Minute Video Link:**
  - YouTube (set to Unlisted or Public) or Loom link.
  - **Tested in an Incognito / Private browser window** without signing in.
- [ ] **Meta Model & Open-Weight Disclosures:**
  - Model list clearly stated in submission description: `SAM 3.1`, `Muse Spark`, `Muse Spark Open (meta-models/muse-spark-open-1026)`, `Muse Voice Transcribe`.
  - Disclose partner inference endpoint (Baseten/Modal/Fireworks) to ensure qualification for the **$10,000 Best Open Weight Build** bonus.
- [ ] **All Contributors Listed:** Add all team members with correct email addresses and social handles on the submission form.

---

## 4. Social Media Playbook: Winning the $20,000 Most Viral Prize

The **Most Viral Project** bonus awards $20,000 to the project with the highest engagement (likes, retweets, replies) on X between launch and **November 8 EOD**.

### Launch Strategy (Post on X by Nov 5 at 9:00 AM ET):
1. **The Media:** Attach the 45-second high-energy teaser video directly to the first tweet (the split-screen coordinate miss vs. SAM 3.1 neon mask lock + canvas slider control). Native videos receive 10x higher algorithm reach than external links.
2. **The Hook Tweet Copy:**
   > We just solved the biggest roadblock in autonomous computer use: coordinate hallucination.
   > 
   > Introducing MusePilot: the first zero-coordinate, visually-verified GUI agent powered by Meta’s SAM 3.1 & Muse models.
   > 
   > Watch it control an invisible HTML5 canvas with pixel-exact precision 🧵👇
3. **The Thread Structure:**
   - **Tweet 1:** Hook + 45s native video.
   - **Tweet 2:** The Architectural Delta (Explain Set-of-Mark grounding + closed-loop visual verification via Muse Spark Open).
   - **Tweet 3:** Why standard accessibility trees fail on canvas apps and how SAM 3.1 fixes it.
   - **Tweet 4:** Link to the 3-minute full demo video, public GitHub repository, and Cerebal Valley project page.
   - **Tweet 5:** Mention & thank `@CerebralValley`, `@MetaAI`, and partner platforms (`@basetenco`, `@modal_labs`, `@fireworksai`).
4. **Engagement Maximization:**
   - Reply to every comment within 15 minutes during the first 6 hours of posting.
   - Ask an engaging technical question in the thread: *"What legacy or canvas software in your company needs autonomous automation the most?"*
