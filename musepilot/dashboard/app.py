# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Real-time Streamlit HUD & Telemetry Dashboard for MusePilot."""

from __future__ import annotations

import streamlit as st

from musepilot.config import get_settings
from musepilot.health.checker import run_health_check
from musepilot.orchestrator import MusePilotOrchestrator
from musepilot.perception import (
    SAM31PerceptionClient,
    ScreenCaptureEngine,
    SetOfMarkRenderer,
)
from musepilot.telemetry import GLOBAL_TELEMETRY
from musepilot.trace import TraceStore


def render_dashboard() -> None:
    """Render the interactive MusePilot HUD and Telemetry Dashboard."""
    st.set_page_config(
        page_title="MusePilot HUD // Zero-Coordinate Multimodal GUI Agent",
        page_icon="🎯",
        layout="wide",
    )

    settings = get_settings()
    store = TraceStore()
    orchestrator = MusePilotOrchestrator(trace_store=store)
    capture = ScreenCaptureEngine(dpi_scale=settings.display_dpi_scale)
    sam_client = SAM31PerceptionClient()
    som_renderer = SetOfMarkRenderer()

    st.title("🎯 MusePilot — Zero-Coordinate Multimodal GUI Agent HUD")
    st.caption(
        "Powered by **Meta SAM 3.1** (Set-of-Mark Grounding) • **Muse Spark** (DAG Planner) • "
        f"**{settings.verifier_model_id}** on **{settings.partner_provider.upper()}** (Closed-Loop Verifier) • "
        "**Muse Voice Transcribe**"
    )

    # Sidebar Controls & Pre-Flight Health Status
    with st.sidebar:
        st.header("⚙️ Agent Control Panel")
        workflow_choice = st.selectbox(
            "Select Frozen Workflow",
            options=["w1", "w2"],
            format_func=lambda w: (
                "W1: Precision WebGL/HTML5 Canvas Calibration"
                if w == "w1"
                else "W2: Voice Cross-App Incident Dispatch + Self-Healing"
            ),
        )
        inject_modal = st.checkbox(
            "Inject Blocking Modal Obstruction (W2 Self-Healing Showcase)",
            value=(workflow_choice == "w2"),
            disabled=(workflow_choice != "w2"),
        )

        col_run, col_replay = st.columns(2)
        run_clicked = col_run.button("🚀 Execute Run", type="primary", use_container_width=True)
        replay_clicked = col_replay.button("🔁 Replay Trace", use_container_width=True)

        st.divider()
        st.subheader("🩺 Pre-Flight Health Check")
        health = run_health_check()
        st.metric("System Status", "READY ✅" if health.passed else "DEGRADED ⚠️")
        st.json(
            {
                "mode": health.execution_mode,
                "sam_3_1": health.sam_model_id,
                "planner": health.planner_model_id,
                "open_weight_verifier": health.verifier_model_id,
                "partner": health.partner_provider,
                "dpi_scale": f"{health.display_dpi_scale}x",
            }
        )

    # Execute or load trace
    if run_clicked:
        with st.spinner(f"Executing closed-loop workflow {workflow_choice.upper()}..."):
            trace = orchestrator.run_workflow(
                workflow_id=workflow_choice,
                use_voice_intake=(workflow_choice == "w2"),
                inject_modal_obstruction=inject_modal,
                save_as_golden=True,
            )
    elif replay_clicked:
        trace = store.load_golden_or_latest(workflow_choice)
        if trace is None:
            trace = orchestrator.run_workflow(
                workflow_id=workflow_choice,
                use_voice_intake=(workflow_choice == "w2"),
                inject_modal_obstruction=inject_modal,
                save_as_golden=True,
            )
    else:
        trace = store.load_golden_or_latest(workflow_choice)
        if trace is None:
            trace = orchestrator.run_workflow(
                workflow_id=workflow_choice,
                use_voice_intake=(workflow_choice == "w2"),
                inject_modal_obstruction=(workflow_choice == "w2"),
                save_as_golden=True,
            )

    # Top-level Quantitative Metrics Row
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric(
        "Mask Centroid Hit Rate",
        f"{trace.metrics.mask_centroid_hit_rate * 100:.0f}%",
        "0px Coordinate Drift",
    )
    m2.metric(
        "Verification Pass Rate",
        f"{trace.metrics.verification_pass_rate * 100:.1f}%",
        settings.verifier_model_id,
    )
    m3.metric(
        "Self-Healing Recoveries", str(trace.metrics.self_healing_recoveries), "Autonomous Replan"
    )
    m4.metric("Display DPI Scale", f"{settings.display_dpi_scale:.1f}x", "Retina Normalized")
    m5.metric(
        "Steps Completed",
        f"{trace.metrics.total_steps_completed} / {trace.metrics.total_steps_planned}",
        trace.status,
    )

    if trace.voice_intake:
        st.info(
            f"🎙️ **Muse Voice Transcribe ({trace.voice_intake.model_id}):** "
            f'"{trace.voice_intake.transcript}" *(Confidence: {trace.voice_intake.confidence * 100:.1f}%)*'
        )

    # Visual Perception & Set-of-Mark (SoM) Comparison
    st.subheader("👁️ SAM 3.1 Set-of-Mark (SoM) Grounding & Visual Verification State")
    state_options = ["initial"]
    if workflow_choice == "w2" and any(r.self_healed for r in trace.records):
        state_options.extend(["step_1", "step_2_modal_blocked", "step_2_recovered", "step_3_final"])
    else:
        for i in range(1, len(trace.plan.steps)):
            state_options.append(f"step_{i}")
        state_options.append(f"step_{len(trace.plan.steps)}_final")

    selected_state = st.select_slider(
        "Inspect Visual State Timeline",
        options=state_options,
        value=state_options[-1],
    )

    frame = capture.render_canvas_state(workflow_id=workflow_choice, state_label=selected_state)
    masks = sam_client.segment_frame(
        frame=frame, workflow_id=workflow_choice, trace_id=trace.trace_id
    )
    verified_ids = {r.step.target_mask_id for r in trace.records if r.verdict.passed}
    active_target = (
        4
        if "modal" in selected_state
        else (trace.records[-1].step.target_mask_id if trace.records else 1)
    )
    som_img = som_renderer.render_som_overlay(
        base_image=frame.image,
        mask_set=masks,
        active_target_mask_id=active_target,
        verified_mask_ids=verified_ids,
    )

    col_raw, col_som = st.columns(2)
    with col_raw:
        st.markdown("**Raw Un-Inspectable HTML5 Canvas Frame (`0 DOM Nodes`)**")
        st.image(frame.image, use_container_width=True)
    with col_som:
        st.markdown("**SAM 3.1 Set-of-Mark (SoM) Segmented Overlay + Centroids**")
        st.image(som_img, use_container_width=True)

    # Step-by-Step Closed-Loop Execution & Verification Ledger
    st.subheader("✅ Closed-Loop Execution & Open-Weight Verification Ledger")
    for idx, rec in enumerate(trace.records, start=1):
        badge = "🟢 VERIFIED PASS" if rec.verdict.passed else "🔴 OBSTRUCTION DETECTED"
        heal_tag = " • 🛠️ SELF-HEALED" if rec.self_healed else ""
        with st.expander(
            f"Event #{idx} | Step {rec.step.step_id} (Attempt {rec.attempt_number}): "
            f"{rec.step.operation.value.upper()} -> SAM 3.1 Mask [#{rec.step.target_mask_id:02d}] | {badge}{heal_tag}",
            expanded=(not rec.verdict.passed or rec.self_healed),
        ):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Planner & DPI-Normalized Execution Receipt**")
                st.json(
                    {
                        "operation": rec.step.operation.value,
                        "target_mask_id": rec.step.target_mask_id,
                        "frame_centroid_px": rec.receipt.frame_centroid_px,
                        "dpi_scale": rec.receipt.dpi_scale,
                        "os_logical_point": rec.receipt.os_logical_point,
                        "redacted_input_value": rec.receipt.redacted_input_value,
                        "reasoning": rec.step.reasoning,
                    }
                )
            with c2:
                st.markdown(f"**Open-Weight Verifier (`{rec.verdict.model_id}`)**")
                st.json(
                    {
                        "passed": rec.verdict.passed,
                        "confidence": rec.verdict.confidence,
                        "roi_pixel_delta": rec.verdict.roi_pixel_delta,
                        "observed_change": rec.verdict.observed_change,
                        "obstruction_detected": rec.verdict.obstruction_detected,
                        "retry_hint": rec.verdict.retry_hint,
                        "healing_action": rec.healing_action,
                    }
                )

    # OpenTelemetry Spans & Trace Export
    with st.expander("📡 OpenTelemetry Spans & Structured Trace Inspector"):
        st.json([s.to_otel_dict() for s in GLOBAL_TELEMETRY.spans])


if __name__ == "__main__":
    render_dashboard()
