// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Quantitative benchmark report models (Milestone M9).
library;

/// Per-workflow benchmark aggregation.
class WorkflowStats {
  const WorkflowStats({
    required this.runs,
    required this.stepsCompleted,
    required this.meanHitRate,
    required this.meanPassRate,
    required this.selfHealingEvents,
  });

  factory WorkflowStats.fromJson(Map<String, dynamic> json) => WorkflowStats(
    runs: (json['runs'] as num?)?.toInt() ?? 0,
    stepsCompleted: json['steps_completed'] as String? ?? '0/0',
    meanHitRate: (json['mean_hit_rate'] as num?)?.toDouble() ?? 0.0,
    meanPassRate: (json['mean_pass_rate'] as num?)?.toDouble() ?? 0.0,
    selfHealingEvents: (json['self_healing_events'] as num?)?.toInt() ?? 0,
  );

  final int runs;
  final String stepsCompleted;
  final double meanHitRate;
  final double meanPassRate;
  final int selfHealingEvents;
}

/// Benchmark report across all historical traces.
class BenchmarkReport {
  const BenchmarkReport({
    required this.totalRunsAnalyzed,
    required this.totalStepsExecuted,
    required this.meanMaskHitRate,
    required this.meanVerificationPassRate,
    required this.totalSelfHealingRecoveries,
    required this.selfHealingSuccessRate,
    required this.samLatencyP50Ms,
    required this.plannerLatencyP50Ms,
    required this.verifierLatencyP50Ms,
    required this.workflows,
  });

  factory BenchmarkReport.fromJson(Map<String, dynamic> json) {
    final rawWorkflows = json['workflows'] as Map? ?? {};
    return BenchmarkReport(
      totalRunsAnalyzed: (json['total_runs_analyzed'] as num?)?.toInt() ?? 0,
      totalStepsExecuted: (json['total_steps_executed'] as num?)?.toInt() ?? 0,
      meanMaskHitRate: (json['mean_mask_hit_rate'] as num?)?.toDouble() ?? 0.0,
      meanVerificationPassRate:
          (json['mean_verification_pass_rate'] as num?)?.toDouble() ?? 0.0,
      totalSelfHealingRecoveries:
          (json['total_self_healing_recoveries'] as num?)?.toInt() ?? 0,
      selfHealingSuccessRate:
          (json['self_healing_success_rate'] as num?)?.toDouble() ?? 0.0,
      samLatencyP50Ms: (json['sam_latency_p50_ms'] as num?)?.toDouble() ?? 0.0,
      plannerLatencyP50Ms:
          (json['planner_latency_p50_ms'] as num?)?.toDouble() ?? 0.0,
      verifierLatencyP50Ms:
          (json['verifier_latency_p50_ms'] as num?)?.toDouble() ?? 0.0,
      workflows: rawWorkflows.map(
        (key, value) => MapEntry(
          key.toString(),
          WorkflowStats.fromJson(value as Map<String, dynamic>),
        ),
      ),
    );
  }

  final int totalRunsAnalyzed;
  final int totalStepsExecuted;
  final double meanMaskHitRate;
  final double meanVerificationPassRate;
  final int totalSelfHealingRecoveries;
  final double selfHealingSuccessRate;
  final double samLatencyP50Ms;
  final double plannerLatencyP50Ms;
  final double verifierLatencyP50Ms;
  final Map<String, WorkflowStats> workflows;
}
