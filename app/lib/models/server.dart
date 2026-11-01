// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Server status models: health, config, workflows, and trace summaries.
library;

/// Pre-flight readiness report (contains no secret material).
class HealthReport {
  const HealthReport({
    required this.passed,
    required this.executionMode,
    required this.samModelId,
    required this.plannerModelId,
    required this.verifierModelId,
    required this.partnerProvider,
    required this.displayDpiScale,
    required this.checks,
    this.voiceModelId = '',
    this.adbAvailable = false,
  });

  factory HealthReport.fromJson(Map<String, dynamic> json) => HealthReport(
    passed: json['passed'] as bool? ?? false,
    executionMode: json['execution_mode'] as String? ?? 'unknown',
    samModelId: json['sam_model_id'] as String? ?? '',
    plannerModelId: json['planner_model_id'] as String? ?? '',
    verifierModelId: json['verifier_model_id'] as String? ?? '',
    partnerProvider: json['partner_provider'] as String? ?? '',
    displayDpiScale: (json['display_dpi_scale'] as num?)?.toDouble() ?? 1.0,
    checks: Map<String, bool>.from(json['checks'] as Map? ?? {}),
    voiceModelId: json['voice_model_id'] as String? ?? '',
    adbAvailable: json['adb_available'] as bool? ?? false,
  );

  final bool passed;
  final String executionMode;
  final String samModelId;
  final String plannerModelId;
  final String verifierModelId;
  final String partnerProvider;
  final double displayDpiScale;
  final Map<String, bool> checks;

  /// Voice transcription model served by the backend (empty when unset).
  final String voiceModelId;

  /// Whether an ADB device is currently reachable from the server.
  ///
  /// The device serial is intentionally not exposed to clients.
  final bool adbAvailable;
}

/// Non-secret runtime configuration served to HUD clients.
class ServerConfig {
  const ServerConfig({
    required this.executionMode,
    required this.displayDpiScale,
    required this.samModelId,
    required this.plannerModelId,
    required this.verifierModelId,
    required this.voiceModelId,
    required this.partnerProvider,
    this.verifierBackend = 'partner',
    this.metaVerifierModelId = '',
  });

  factory ServerConfig.fromJson(Map<String, dynamic> json) => ServerConfig(
    executionMode: json['execution_mode'] as String? ?? 'unknown',
    displayDpiScale: (json['display_dpi_scale'] as num?)?.toDouble() ?? 1.0,
    samModelId: json['sam_model_id'] as String? ?? '',
    plannerModelId: json['planner_model_id'] as String? ?? '',
    verifierModelId: json['verifier_model_id'] as String? ?? '',
    voiceModelId: json['voice_model_id'] as String? ?? '',
    partnerProvider: json['partner_provider'] as String? ?? '',
    verifierBackend: json['verifier_backend'] as String? ?? 'partner',
    metaVerifierModelId: json['meta_verifier_model_id'] as String? ?? '',
  );

  final String executionMode;
  final double displayDpiScale;
  final String samModelId;
  final String plannerModelId;
  final String verifierModelId;
  final String voiceModelId;
  final String partnerProvider;

  /// Active verification backend: `partner` (open-weight model) or `meta`.
  final String verifierBackend;

  /// Verifier model used when [verifierBackend] is `meta`.
  final String metaVerifierModelId;

  /// Short human-readable label for the active verifier.
  String get verifierDisplayName {
    final id = verifierBackend == 'meta'
        ? metaVerifierModelId
        : verifierModelId;
    if (id.isEmpty) return 'Verifier';
    final short = id.split('/').last;
    if (short.startsWith('muse-spark-open')) return 'Spark Open verifier';
    if (short.startsWith('muse-spark')) return 'Muse Spark verifier';
    if (short.startsWith('muse-glimmer')) return 'Muse Glimmer verifier';
    return short;
  }
}

/// Frozen workflow descriptor.
class WorkflowInfo {
  const WorkflowInfo({
    required this.workflowId,
    required this.title,
    required this.description,
  });

  factory WorkflowInfo.fromJson(Map<String, dynamic> json) => WorkflowInfo(
    workflowId: json['workflow_id'] as String? ?? '',
    title: json['title'] as String? ?? '',
    description: json['description'] as String? ?? '',
  );

  final String workflowId;
  final String title;
  final String description;
}

/// Lightweight run-trace listing entry.
class TraceSummary {
  const TraceSummary({
    required this.traceId,
    required this.workflowId,
    required this.status,
    required this.createdAt,
    required this.stepsCompleted,
    required this.stepsPlanned,
    required this.verificationPassRate,
    required this.selfHealingRecoveries,
  });

  factory TraceSummary.fromJson(Map<String, dynamic> json) => TraceSummary(
    traceId: json['trace_id'] as String? ?? '',
    workflowId: json['workflow_id'] as String? ?? '',
    status: json['status'] as String? ?? '',
    createdAt: json['created_at'] as String? ?? '',
    stepsCompleted: (json['steps_completed'] as num?)?.toInt() ?? 0,
    stepsPlanned: (json['steps_planned'] as num?)?.toInt() ?? 0,
    verificationPassRate:
        (json['verification_pass_rate'] as num?)?.toDouble() ?? 0.0,
    selfHealingRecoveries:
        (json['self_healing_recoveries'] as num?)?.toInt() ?? 0,
  );

  final String traceId;
  final String workflowId;
  final String status;
  final String createdAt;
  final int stepsCompleted;
  final int stepsPlanned;
  final double verificationPassRate;
  final int selfHealingRecoveries;
}
