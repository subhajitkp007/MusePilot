// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Strictly-typed run-trace models mirroring `musepilot/contracts/schemas.py`.
///
/// The client never synthesizes coordinates: every pixel value shown comes
/// from a server-issued receipt, preserving the Zero-Coordinate Invariant.
library;

int _asInt(Object? value, String field) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  throw FormatException('Expected int for $field, got $value');
}

double _asDouble(Object? value, String field) {
  if (value is num) return value.toDouble();
  throw FormatException('Expected number for $field, got $value');
}

String _asString(Object? value, String field) {
  if (value is String) return value;
  throw FormatException('Expected string for $field, got $value');
}

List<int> _asIntList(Object? value, String field) {
  if (value is List) return value.map((e) => _asInt(e, field)).toList();
  throw FormatException('Expected list for $field, got $value');
}

List<double> _asDoubleList(Object? value, String field) {
  if (value is List) return value.map((e) => _asDouble(e, field)).toList();
  throw FormatException('Expected list for $field, got $value');
}

/// Pixel-exact UI segment metadata produced by Meta SAM 3.1.
class MaskMetadata {
  const MaskMetadata({
    required this.maskId,
    required this.bbox,
    required this.centroidPx,
    required this.areaPx,
    required this.confidence,
    required this.semanticTag,
  });

  factory MaskMetadata.fromJson(Map<String, dynamic> json) => MaskMetadata(
    maskId: _asInt(json['mask_id'], 'mask_id'),
    bbox: _asIntList(json['bbox'], 'bbox'),
    centroidPx: _asIntList(json['centroid_px'], 'centroid_px'),
    areaPx: _asInt(json['area_px'], 'area_px'),
    confidence: _asDouble(json['confidence'], 'confidence'),
    semanticTag: json['semantic_tag'] as String? ?? 'ui_element',
  );

  final int maskId;
  final List<int> bbox;
  final List<int> centroidPx;
  final int areaPx;
  final double confidence;
  final String semanticTag;
}

/// Collection of SAM 3.1 masks for a single captured frame.
class MaskSet {
  const MaskSet({
    required this.screenHash,
    required this.widthPx,
    required this.heightPx,
    required this.dpiScale,
    required this.modelId,
    required this.masks,
  });

  factory MaskSet.fromJson(Map<String, dynamic> json) => MaskSet(
    screenHash: _asString(json['screen_hash'], 'screen_hash'),
    widthPx: _asInt(json['width_px'], 'width_px'),
    heightPx: _asInt(json['height_px'], 'height_px'),
    dpiScale: _asDouble(json['dpi_scale'], 'dpi_scale'),
    modelId: json['model_id'] as String? ?? 'meta-models/sam-3.1',
    masks: (json['masks'] as List? ?? [])
        .map((m) => MaskMetadata.fromJson(m as Map<String, dynamic>))
        .toList(),
  );

  final String screenHash;
  final int widthPx;
  final int heightPx;
  final double dpiScale;
  final String modelId;
  final List<MaskMetadata> masks;
}

/// A planned action referencing a SAM 3.1 mask ID (never coordinates).
class StepNode {
  const StepNode({
    required this.stepId,
    required this.operation,
    required this.targetMaskId,
    this.dragToMaskId,
    this.inputValue,
    required this.isSensitive,
    required this.isDestructive,
    required this.expectedOutcome,
    required this.reasoning,
  });

  factory StepNode.fromJson(Map<String, dynamic> json) => StepNode(
    stepId: _asInt(json['step_id'], 'step_id'),
    operation: _asString(json['operation'], 'operation'),
    targetMaskId: _asInt(json['target_mask_id'], 'target_mask_id'),
    dragToMaskId: json['drag_to_mask_id'] as int?,
    inputValue: json['input_value'] as String?,
    isSensitive: json['is_sensitive'] as bool? ?? false,
    isDestructive: json['is_destructive'] as bool? ?? false,
    expectedOutcome: _asString(json['expected_outcome'], 'expected_outcome'),
    reasoning: json['reasoning'] as String? ?? '',
  );

  final int stepId;
  final String operation;
  final int targetMaskId;
  final int? dragToMaskId;
  final String? inputValue;
  final bool isSensitive;
  final bool isDestructive;
  final String expectedOutcome;
  final String reasoning;
}

/// Structured multi-step plan emitted by Muse Spark.
class StepDag {
  const StepDag({
    required this.workflowId,
    required this.intent,
    required this.planSummary,
    required this.steps,
  });

  factory StepDag.fromJson(Map<String, dynamic> json) => StepDag(
    workflowId: _asString(json['workflow_id'], 'workflow_id'),
    intent: _asString(json['intent'], 'intent'),
    planSummary: _asString(json['plan_summary'], 'plan_summary'),
    steps: (json['steps'] as List? ?? [])
        .map((s) => StepNode.fromJson(s as Map<String, dynamic>))
        .toList(),
  );

  final String workflowId;
  final String intent;
  final String planSummary;
  final List<StepNode> steps;
}

/// Execution receipt proving DPI-normalized centroid translation.
class ActionReceipt {
  const ActionReceipt({
    required this.stepId,
    required this.operation,
    required this.targetMaskId,
    required this.frameCentroidPx,
    required this.dpiScale,
    required this.osLogicalPoint,
    this.redactedInputValue,
    required this.preFrameHash,
    required this.postFrameHash,
    required this.executionLatencyMs,
  });

  factory ActionReceipt.fromJson(Map<String, dynamic> json) => ActionReceipt(
    stepId: _asInt(json['step_id'], 'step_id'),
    operation: _asString(json['operation'], 'operation'),
    targetMaskId: _asInt(json['target_mask_id'], 'target_mask_id'),
    frameCentroidPx: _asIntList(json['frame_centroid_px'], 'frame_centroid_px'),
    dpiScale: _asDouble(json['dpi_scale'], 'dpi_scale'),
    osLogicalPoint: _asDoubleList(json['os_logical_point'], 'os_logical_point'),
    redactedInputValue: json['redacted_input_value'] as String?,
    preFrameHash: _asString(json['pre_frame_hash'], 'pre_frame_hash'),
    postFrameHash: _asString(json['post_frame_hash'], 'post_frame_hash'),
    executionLatencyMs: _asDouble(
      json['execution_latency_ms'],
      'execution_latency_ms',
    ),
  );

  final int stepId;
  final String operation;
  final int targetMaskId;
  final List<int> frameCentroidPx;
  final double dpiScale;
  final List<double> osLogicalPoint;
  final String? redactedInputValue;
  final String preFrameHash;
  final String postFrameHash;
  final double executionLatencyMs;
}

/// Closed-loop verification verdict from Muse Spark Open.
class VerificationVerdict {
  const VerificationVerdict({
    required this.modelId,
    required this.partnerProvider,
    required this.passed,
    required this.confidence,
    required this.roiPixelDelta,
    required this.observedChange,
    required this.obstructionDetected,
    this.retryHint,
    required this.latencyMs,
  });

  factory VerificationVerdict.fromJson(Map<String, dynamic> json) =>
      VerificationVerdict(
        modelId:
            json['model_id'] as String? ?? 'meta-models/muse-spark-open-1026',
        partnerProvider: json['partner_provider'] as String? ?? 'baseten',
        passed: json['passed'] as bool? ?? false,
        confidence: _asDouble(json['confidence'], 'confidence'),
        roiPixelDelta: _asDouble(json['roi_pixel_delta'], 'roi_pixel_delta'),
        observedChange: _asString(json['observed_change'], 'observed_change'),
        obstructionDetected: json['obstruction_detected'] as bool? ?? false,
        retryHint: json['retry_hint'] as String?,
        latencyMs: _asDouble(json['latency_ms'], 'latency_ms'),
      );

  final String modelId;
  final String partnerProvider;
  final bool passed;
  final double confidence;
  final double roiPixelDelta;
  final String observedChange;
  final bool obstructionDetected;
  final String? retryHint;
  final double latencyMs;
}

/// Spoken intent transcribed via Muse Voice Transcribe.
class VoiceTranscript {
  const VoiceTranscript({
    required this.modelId,
    required this.transcript,
    required this.confidence,
  });

  factory VoiceTranscript.fromJson(Map<String, dynamic> json) =>
      VoiceTranscript(
        modelId:
            json['model_id'] as String? ?? 'meta-models/muse-voice-transcribe',
        transcript: _asString(json['transcript'], 'transcript'),
        confidence: _asDouble(json['confidence'], 'confidence'),
      );

  final String modelId;
  final String transcript;
  final double confidence;
}

/// Complete audit record for a single step attempt.
class StepExecutionRecord {
  const StepExecutionRecord({
    required this.attemptNumber,
    required this.step,
    required this.receipt,
    required this.verdict,
    required this.selfHealed,
    this.healingAction,
  });

  factory StepExecutionRecord.fromJson(Map<String, dynamic> json) =>
      StepExecutionRecord(
        attemptNumber: _asInt(json['attempt_number'], 'attempt_number'),
        step: StepNode.fromJson(json['step'] as Map<String, dynamic>),
        receipt: ActionReceipt.fromJson(
          json['receipt'] as Map<String, dynamic>,
        ),
        verdict: VerificationVerdict.fromJson(
          json['verdict'] as Map<String, dynamic>,
        ),
        selfHealed: json['self_healed'] as bool? ?? false,
        healingAction: json['healing_action'] as String?,
      );

  final int attemptNumber;
  final StepNode step;
  final ActionReceipt receipt;
  final VerificationVerdict verdict;
  final bool selfHealed;
  final String? healingAction;
}

/// Quantitative metrics computed over a run trace.
class MetricsSummary {
  const MetricsSummary({
    required this.totalStepsPlanned,
    required this.totalStepsCompleted,
    required this.maskCentroidHitRate,
    required this.verificationPassRate,
    required this.selfHealingRecoveries,
    required this.medianSamLatencyMs,
    required this.medianPlannerLatencyMs,
    required this.medianVerifierLatencyMs,
  });

  factory MetricsSummary.fromJson(Map<String, dynamic> json) => MetricsSummary(
    totalStepsPlanned: _asInt(
      json['total_steps_planned'],
      'total_steps_planned',
    ),
    totalStepsCompleted: _asInt(
      json['total_steps_completed'],
      'total_steps_completed',
    ),
    maskCentroidHitRate: _asDouble(
      json['mask_centroid_hit_rate'],
      'mask_centroid_hit_rate',
    ),
    verificationPassRate: _asDouble(
      json['verification_pass_rate'],
      'verification_pass_rate',
    ),
    selfHealingRecoveries: _asInt(
      json['self_healing_recoveries'],
      'self_healing_recoveries',
    ),
    medianSamLatencyMs: _asDouble(
      json['median_sam_latency_ms'],
      'median_sam_latency_ms',
    ),
    medianPlannerLatencyMs: _asDouble(
      json['median_planner_latency_ms'],
      'median_planner_latency_ms',
    ),
    medianVerifierLatencyMs: _asDouble(
      json['median_verifier_latency_ms'],
      'median_verifier_latency_ms',
    ),
  );

  final int totalStepsPlanned;
  final int totalStepsCompleted;
  final double maskCentroidHitRate;
  final double verificationPassRate;
  final int selfHealingRecoveries;
  final double medianSamLatencyMs;
  final double medianPlannerLatencyMs;
  final double medianVerifierLatencyMs;
}

/// Replayable, deterministic full-run trace.
class RunTrace {
  const RunTrace({
    required this.traceId,
    required this.workflowId,
    required this.createdAt,
    required this.executionMode,
    this.voiceIntake,
    required this.initialMaskSet,
    required this.plan,
    required this.records,
    required this.status,
    required this.metrics,
  });

  factory RunTrace.fromJson(Map<String, dynamic> json) {
    final voice = json['voice_intake'];
    return RunTrace(
      traceId: _asString(json['trace_id'], 'trace_id'),
      workflowId: _asString(json['workflow_id'], 'workflow_id'),
      createdAt: _asString(json['created_at'], 'created_at'),
      executionMode: _asString(json['execution_mode'], 'execution_mode'),
      voiceIntake: voice == null
          ? null
          : VoiceTranscript.fromJson(voice as Map<String, dynamic>),
      initialMaskSet: MaskSet.fromJson(
        json['initial_mask_set'] as Map<String, dynamic>,
      ),
      plan: StepDag.fromJson(json['plan'] as Map<String, dynamic>),
      records: (json['records'] as List? ?? [])
          .map((r) => StepExecutionRecord.fromJson(r as Map<String, dynamic>))
          .toList(),
      status: json['status'] as String? ?? 'COMPLETED',
      metrics: MetricsSummary.fromJson(json['metrics'] as Map<String, dynamic>),
    );
  }

  final String traceId;
  final String workflowId;
  final String createdAt;
  final String executionMode;
  final VoiceTranscript? voiceIntake;
  final MaskSet initialMaskSet;
  final StepDag plan;
  final List<StepExecutionRecord> records;
  final String status;
  final MetricsSummary metrics;
}
