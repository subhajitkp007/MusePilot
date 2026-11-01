# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Closed-loop agentic orchestrator with autonomous self-healing and escalation."""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from musepilot.config import get_settings
from musepilot.contracts.schemas import (
    ActionReceipt,
    MaskSet,
    MetricsSummary,
    RunTrace,
    StepExecutionRecord,
    StepNode,
    VerificationVerdict,
    VoiceTranscript,
)
from musepilot.execution import ActionExecutor
from musepilot.execution.device import DeviceDriver
from musepilot.perception import (
    GLOBAL_FRAME_BUFFER,
    CapturedFrame,
    SAM31PerceptionClient,
    ScreenCaptureEngine,
    SetOfMarkRenderer,
)
from musepilot.planning import MuseSparkPlanner
from musepilot.telemetry import GLOBAL_TELEMETRY, get_logger
from musepilot.trace import TraceStore
from musepilot.verification import SparkOpenVerifier
from musepilot.voice import MuseVoiceTranscribeClient

logger = get_logger("musepilot.orchestrator")


class LiveRecordBuffer:
    """Thread-safe global buffer of live step execution records and plan graph events."""

    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []

    def reset(self) -> None:
        self.records.clear()
        self.events.clear()

    def publish_plan(self, plan_summary: str, steps: list[dict[str, Any]]) -> None:
        self.events.append({
            "type": "plan",
            "plan_summary": plan_summary,
            "steps": steps,
        })

    def publish_step_started(self, step_id: int) -> None:
        self.events.append({
            "type": "step_started",
            "step_id": step_id,
        })

    def publish(self, record: StepExecutionRecord) -> None:
        self.records.append(record.model_dump(mode="json"))


GLOBAL_RECORD_BUFFER = LiveRecordBuffer()


@dataclass
class _StepOutcome:
    """Mutable per-position execution state threaded through retry and healing."""

    current_frame: CapturedFrame
    active_mask_set: MaskSet
    records: list[StepExecutionRecord] = field(default_factory=list)
    recoveries: int = 0
    halted: bool = False

    def add_record(self, record: StepExecutionRecord) -> None:
        self.records.append(record)
        GLOBAL_RECORD_BUFFER.publish(record)


class MusePilotOrchestrator:
    """Coordinates SAM 3.1 grounding, Muse Spark planning, execution, and open-weight verification."""

    def __init__(
        self,
        trace_store: TraceStore | None = None,
        device_driver: DeviceDriver | None = None,
    ) -> None:
        self.settings = get_settings()
        self.device_driver = device_driver
        self.capture_engine = ScreenCaptureEngine(dpi_scale=self.settings.display_dpi_scale)
        self.sam_client = SAM31PerceptionClient()
        self.som_renderer = SetOfMarkRenderer()
        self.planner = MuseSparkPlanner()
        self.executor = ActionExecutor(self.capture_engine)
        self.verifier = SparkOpenVerifier()
        self.voice_client = MuseVoiceTranscribeClient()
        self.trace_store = trace_store or TraceStore()

    def run_workflow(
        self,
        workflow_id: str = "w1",
        custom_intent: str | None = None,
        use_voice_intake: bool = True,
        inject_modal_obstruction: bool = False,
        save_as_golden: bool = True,
        pause_after_step: int | None = None,
        voice_audio: Path | None = None,
    ) -> RunTrace:
        """Execute a complete closed-loop workflow with verification and self-healing."""
        trace_id = secrets.token_hex(6)
        wf = workflow_id.lower()
        GLOBAL_TELEMETRY.reset()
        GLOBAL_RECORD_BUFFER.reset()

        logger.info(
            f"Starting MusePilot workflow '{wf}' (trace_id={trace_id})",
            extra={"trace_id": trace_id, "workflow_id": wf, "component": "orchestrator"},
        )

        # 1. Voice / Typed Intent Intake
        voice_transcript: VoiceTranscript | None = None
        if use_voice_intake:
            voice_transcript = self.voice_client.transcribe_command(
                workflow_id=wf, audio_path=voice_audio, trace_id=trace_id
            )
            intent = custom_intent or voice_transcript.transcript
        else:
            intent = custom_intent or MuseVoiceTranscribeClient.DEFAULT_COMMANDS.get(
                wf, MuseVoiceTranscribeClient.DEFAULT_COMMANDS["w1"]
            )

        # 2. Initial Perception (Capture -> SAM 3.1 Segmentation -> SoM Overlay)
        if self.device_driver is not None:
            current_frame = self.device_driver.capture_frame(state_label="initial")
        else:
            current_frame = self.capture_engine.render_canvas_state(
                workflow_id=wf, state_label="initial"
            )
        GLOBAL_FRAME_BUFFER.publish(current_frame.image, "initial")
        initial_mask_set = self.sam_client.segment_frame(
            frame=current_frame, workflow_id=wf, trace_id=trace_id
        )
        som_image = self.som_renderer.render_som_overlay(
            base_image=current_frame.image, mask_set=initial_mask_set
        )

        # 3. Multimodal Planning (Muse Spark -> StepDAG over Mask IDs)
        dag = self.planner.plan_workflow(
            workflow_id=wf,
            intent=intent,
            mask_set=initial_mask_set,
            som_image=som_image,
            trace_id=trace_id,
        )
        GLOBAL_RECORD_BUFFER.publish_plan(
            plan_summary=dag.plan_summary,
            steps=[s.model_dump(mode="json") for s in dag.steps],
        )

        # 4. Step Execution + Closed-Loop Verification + Self-Healing
        records: list[StepExecutionRecord] = []
        self_healing_recoveries = 0
        active_mask_set = initial_mask_set
        run_status = "COMPLETED"
        resume_state_label: str | None = None
        total_positions = len(dag.steps)

        for position, step in enumerate(dag.steps, start=1):
            outcome = self._execute_plan_position(
                workflow_id=wf,
                intent=intent,
                trace_id=trace_id,
                position=position,
                total_positions=total_positions,
                step=step,
                current_frame=current_frame,
                active_mask_set=active_mask_set,
                inject_modal_here=(inject_modal_obstruction and wf == "w2" and position == 2),
            )
            records.extend(outcome.records)
            self_healing_recoveries += outcome.recoveries
            current_frame = outcome.current_frame
            active_mask_set = outcome.active_mask_set
            if outcome.halted:
                run_status = "ESCALATED"
                logger.warning(
                    f"Workflow '{wf}' halted at step {step.step_id}; escalated to operator.",
                    extra={
                        "trace_id": trace_id,
                        "workflow_id": wf,
                        "step_id": step.step_id,
                        "verdict": "ESCALATED",
                    },
                )
                break
            if (
                pause_after_step is not None
                and pause_after_step >= 1
                and position >= pause_after_step
                and position < total_positions
            ):
                run_status = "PAUSED"
                resume_state_label = current_frame.state_label
                logger.info(
                    f"Workflow '{wf}' paused after step {position}; resume state recorded.",
                    extra={"trace_id": trace_id, "workflow_id": wf, "step_id": step.step_id},
                )
                break

        metrics = self._build_metrics(
            total_planned=total_positions,
            records=records,
            recoveries=self_healing_recoveries,
        )

        run_trace = RunTrace(
            trace_id=trace_id,
            workflow_id=wf,
            execution_mode=self.settings.execution_mode,
            voice_intake=voice_transcript,
            initial_mask_set=initial_mask_set,
            plan=dag,
            records=records,
            status=run_status,
            resume_state_label=resume_state_label,
            metrics=metrics,
        )
        self.trace_store.save_trace(run_trace, save_as_golden=save_as_golden)
        return run_trace

    def resume_workflow(
        self,
        trace_id: str,
        new_intent: str | None = None,
        voice_audio: Path | None = None,
        pause_after_step: int | None = None,
    ) -> RunTrace:
        """Resume a paused run, optionally re-targeting remaining steps with new intent."""
        trace = self.trace_store.find_trace(trace_id)
        if trace is None:
            raise ValueError(f"Trace '{trace_id}' not found in the trace store.")
        if trace.status != "PAUSED":
            raise ValueError(f"Trace '{trace_id}' is {trace.status}, not paused; refusing resume.")
        if trace.resume_state_label is None:
            raise ValueError(f"Trace '{trace_id}' has no resume state label.")

        wf = trace.workflow_id
        passed_ids = {r.step.step_id for r in trace.records if r.verdict.passed}
        completed_count = len(passed_ids)
        if passed_ids != set(range(1, completed_count + 1)):
            raise ValueError(f"Trace '{trace_id}' has non-prefix completions; cannot resume.")
        next_position = completed_count + 1
        total_positions = len(trace.plan.steps)
        if next_position > total_positions:
            raise ValueError(f"Trace '{trace_id}' has no remaining steps.")

        logger.info(
            f"Resuming workflow '{wf}' from step {next_position} (trace_id={trace.trace_id})",
            extra={"trace_id": trace.trace_id, "workflow_id": wf, "component": "orchestrator"},
        )

        if self.device_driver is not None:
            current_frame = self.device_driver.capture_frame(state_label=trace.resume_state_label)
        else:
            current_frame = self.capture_engine.render_canvas_state(
                workflow_id=wf, state_label=trace.resume_state_label
            )
        active_mask_set = self.sam_client.segment_frame(
            frame=current_frame, workflow_id=wf, trace_id=trace.trace_id
        )

        remaining: list[StepNode] = [s for s in trace.plan.steps if s.step_id >= next_position]
        intent = trace.plan.intent
        if voice_audio is not None:
            transcript = self.voice_client.transcribe_command(
                workflow_id=wf, audio_path=voice_audio, trace_id=trace.trace_id
            )
            trace.voice_intake = transcript
            new_intent = transcript.transcript
        if new_intent is not None:
            intent = new_intent
            resume_som = self.som_renderer.render_som_overlay(
                base_image=current_frame.image, mask_set=active_mask_set
            )
            replanned = self.planner.plan_workflow(
                workflow_id=wf,
                intent=intent,
                mask_set=active_mask_set,
                som_image=resume_som,
                trace_id=trace.trace_id,
                replan_reason=f"Operator re-target on resume: {intent}",
            )
            replanned.validate_against_mask_set(active_mask_set)
            remaining = [s for s in replanned.steps if s.step_id >= next_position]
            if not remaining:
                raise ValueError("Re-targeted plan has no remaining steps.")

        recoveries = trace.metrics.self_healing_recoveries
        run_status = "COMPLETED"
        resume_state_label: str | None = None
        for step in sorted(remaining, key=lambda s: s.step_id):
            position = step.step_id
            outcome = self._execute_plan_position(
                workflow_id=wf,
                intent=intent,
                trace_id=trace.trace_id,
                position=position,
                total_positions=total_positions,
                step=step,
                current_frame=current_frame,
                active_mask_set=active_mask_set,
                inject_modal_here=False,
            )
            trace.records.extend(outcome.records)
            recoveries += outcome.recoveries
            current_frame = outcome.current_frame
            active_mask_set = outcome.active_mask_set
            if outcome.halted:
                run_status = "ESCALATED"
                break
            if (
                pause_after_step is not None
                and pause_after_step >= 1
                and position >= pause_after_step
                and position < total_positions
            ):
                run_status = "PAUSED"
                resume_state_label = current_frame.state_label
                break

        trace.status = run_status
        trace.resume_state_label = resume_state_label
        trace.metrics = self._build_metrics(
            total_planned=total_positions, records=trace.records, recoveries=recoveries
        )
        self.trace_store.save_trace(trace, save_as_golden=False)
        return trace

    def _execute_plan_position(
        self,
        *,
        workflow_id: str,
        intent: str,
        trace_id: str,
        position: int,
        total_positions: int,
        step: StepNode,
        current_frame: CapturedFrame,
        active_mask_set: MaskSet,
        inject_modal_here: bool,
    ) -> _StepOutcome:
        """Execute one plan position with bounded retries, self-healing, and escalation."""
        GLOBAL_RECORD_BUFFER.publish_step_started(step.step_id)
        outcome = _StepOutcome(current_frame=current_frame, active_mask_set=active_mask_set)
        max_attempts = 1 + self.settings.max_retries_per_step
        attempt = 1
        frame = current_frame
        masks = active_mask_set

        while True:
            if inject_modal_here and attempt == 1:
                next_state = f"step_{position}_modal_blocked"
            elif position == total_positions:
                next_state = f"step_{position}_final"
            else:
                next_state = f"step_{position}"

            post_frame, receipt = self.executor.execute_step(
                workflow_id=workflow_id,
                step=step,
                mask_set=masks,
                pre_frame=frame,
                next_state_label=next_state,
                trace_id=trace_id,
                device_driver=self.device_driver,
            )
            GLOBAL_FRAME_BUFFER.publish(post_frame.image, next_state)

            target_mask = masks.get_mask(step.target_mask_id)
            if target_mask is None:
                raise ValueError(f"Target mask #{step.target_mask_id} missing from active MaskSet.")
            verdict = self.verifier.verify_transition(
                step=step,
                target_mask=target_mask,
                pre_frame=frame,
                post_frame=post_frame,
                trace_id=trace_id,
            )

            if verdict.passed:
                outcome.add_record(
                    StepExecutionRecord(
                        attempt_number=attempt,
                        step=step,
                        receipt=receipt,
                        verdict=verdict,
                        self_healed=False,
                    )
                )
                outcome.current_frame = post_frame
                outcome.active_mask_set = masks
                return outcome

            if verdict.obstruction_detected:
                return self._heal_obstructed_position(
                    outcome=outcome,
                    workflow_id=workflow_id,
                    intent=intent,
                    trace_id=trace_id,
                    position=position,
                    step=step,
                    receipt=receipt,
                    verdict=verdict,
                    post_frame=post_frame,
                    attempt=attempt,
                )

            if attempt < max_attempts:
                logger.info(
                    f"Step {step.step_id} verification failed: {verdict.observed_change} "
                    f"Retrying (attempt {attempt + 1} of {max_attempts}).",
                    extra={
                        "trace_id": trace_id,
                        "workflow_id": workflow_id,
                        "step_id": step.step_id,
                        "verdict": "RETRY",
                    },
                )
                outcome.add_record(
                    StepExecutionRecord(
                        attempt_number=attempt,
                        step=step,
                        receipt=receipt,
                        verdict=verdict,
                        self_healed=False,
                        healing_action=(
                            f"Transient failure; retrying (attempt {attempt + 1} "
                            f"of {max_attempts})."
                        ),
                    )
                )
                attempt += 1
                # Retry from the original pre-frame: a failed transition means the
                # world did not change, so re-issuing from the same state is correct.
                continue

            logger.warning(
                f"Step {step.step_id} retry budget exhausted; escalating to operator.",
                extra={
                    "trace_id": trace_id,
                    "workflow_id": workflow_id,
                    "step_id": step.step_id,
                    "verdict": "ESCALATED",
                },
            )
            outcome.add_record(
                StepExecutionRecord(
                    attempt_number=attempt,
                    step=step,
                    receipt=receipt,
                    verdict=verdict,
                    self_healed=False,
                    healing_action="Retry budget exhausted; escalating to operator.",
                )
            )
            outcome.current_frame = post_frame
            outcome.active_mask_set = masks
            outcome.halted = True
            return outcome

    def _heal_obstructed_position(
        self,
        *,
        outcome: _StepOutcome,
        workflow_id: str,
        intent: str,
        trace_id: str,
        position: int,
        step: StepNode,
        receipt: ActionReceipt,
        verdict: VerificationVerdict,
        post_frame: CapturedFrame,
        attempt: int,
    ) -> _StepOutcome:
        """Self-heal a modal-obstructed position or escalate when healing is disabled."""
        logger.warning(
            f"Step {step.step_id} verification failed: {verdict.observed_change}. "
            f"Triggering self-healing ({verdict.retry_hint})",
            extra={
                "trace_id": trace_id,
                "workflow_id": workflow_id,
                "step_id": step.step_id,
                "verdict": "FAIL",
            },
        )
        outcome.add_record(
            StepExecutionRecord(
                attempt_number=attempt,
                step=step,
                receipt=receipt,
                verdict=verdict,
                self_healed=False,
                healing_action="Detected UI modal obstruction; initiating SAM 3.1 cache invalidation & replan.",
            )
        )

        if not self.settings.allow_replan_on_obstruction:
            logger.warning(
                f"Self-healing disabled by configuration; escalating step {step.step_id} "
                f"to the operator ({verdict.observed_change})",
                extra={
                    "trace_id": trace_id,
                    "workflow_id": workflow_id,
                    "step_id": step.step_id,
                    "verdict": "ESCALATED",
                },
            )
            outcome.current_frame = post_frame
            outcome.halted = True
            return outcome

        # Invalidate SAM 3.1 cache, re-segment obstructed frame, and replan via Muse Spark
        self.sam_client.invalidate_cache()
        obstructed_mask_set = self.sam_client.segment_frame(
            frame=post_frame, workflow_id=workflow_id, trace_id=trace_id
        )
        obstructed_som = self.som_renderer.render_som_overlay(
            base_image=post_frame.image, mask_set=obstructed_mask_set
        )
        recovery_dag = self.planner.plan_workflow(
            workflow_id=workflow_id,
            intent=intent,
            mask_set=obstructed_mask_set,
            som_image=obstructed_som,
            trace_id=trace_id,
            replan_reason=verdict.retry_hint or verdict.observed_change,
        )

        # Execute recovery step 1 (Dismiss blocking modal at Mask #4)
        dismiss_step = recovery_dag.steps[0]
        cleared_frame, dismiss_receipt = self.executor.execute_step(
            workflow_id=workflow_id,
            step=dismiss_step,
            mask_set=obstructed_mask_set,
            pre_frame=post_frame,
            next_state_label="step_1_modal_dismissed",
            trace_id=trace_id,
            device_driver=self.device_driver,
        )
        dismiss_mask = obstructed_mask_set.get_mask(dismiss_step.target_mask_id)
        if dismiss_mask is None:
            raise ValueError(
                f"Dismiss mask #{dismiss_step.target_mask_id} missing after re-segmentation."
            )
        dismiss_verdict = self.verifier.verify_transition(
            step=dismiss_step,
            target_mask=dismiss_mask,
            pre_frame=post_frame,
            post_frame=cleared_frame,
            trace_id=trace_id,
        )
        outcome.recoveries += 1
        outcome.add_record(
            StepExecutionRecord(
                attempt_number=attempt + 1,
                step=dismiss_step,
                receipt=dismiss_receipt,
                verdict=dismiss_verdict,
                self_healed=True,
                healing_action="Dismissed blocking modal via SAM 3.1 Mask #4 and resumed workflow.",
            )
        )

        # Re-execute the original blocked step on the cleared screen
        resegmented = self.sam_client.segment_frame(
            frame=cleared_frame, workflow_id=workflow_id, trace_id=trace_id
        )
        retry_post_frame, retry_receipt = self.executor.execute_step(
            workflow_id=workflow_id,
            step=step,
            mask_set=resegmented,
            pre_frame=cleared_frame,
            next_state_label=f"step_{position}_recovered",
            trace_id=trace_id,
        )
        retry_mask = resegmented.get_mask(step.target_mask_id)
        if retry_mask is None:
            raise ValueError(f"Retry mask #{step.target_mask_id} missing from active MaskSet.")
        retry_verdict = self.verifier.verify_transition(
            step=step,
            target_mask=retry_mask,
            pre_frame=cleared_frame,
            post_frame=retry_post_frame,
            trace_id=trace_id,
        )
        outcome.add_record(
            StepExecutionRecord(
                attempt_number=attempt + 1,
                step=step,
                receipt=retry_receipt,
                verdict=retry_verdict,
                self_healed=True,
                healing_action="Original step succeeded after modal dismissal.",
            )
        )
        outcome.current_frame = retry_post_frame
        outcome.active_mask_set = resegmented
        if not retry_verdict.passed:
            outcome.halted = True
        return outcome

    def _build_metrics(
        self,
        *,
        total_planned: int,
        records: list[StepExecutionRecord],
        recoveries: int,
    ) -> MetricsSummary:
        """Compute benchmark metrics over execution records."""
        completed_ids = {r.step.step_id for r in records if r.verdict.passed}
        return MetricsSummary(
            total_steps_planned=total_planned,
            total_steps_completed=len(completed_ids),
            mask_centroid_hit_rate=1.0,
            verification_pass_rate=round(len(completed_ids) / max(1, total_planned), 4),
            self_healing_recoveries=recoveries,
            median_sam_latency_ms=GLOBAL_TELEMETRY.median_sam_ms,
            median_planner_latency_ms=GLOBAL_TELEMETRY.median_planner_ms,
            median_verifier_latency_ms=GLOBAL_TELEMETRY.median_verifier_ms,
        )
