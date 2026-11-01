// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Contract tests: golden-trace parsing and the Zero-Coordinate Invariant.
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:musepilot_hud/models/benchmark.dart';
import 'package:musepilot_hud/models/server.dart';
import 'package:musepilot_hud/models/trace.dart';

Map<String, dynamic> _fixture(String name) =>
    jsonDecode(
          File('test/fixtures/$name').readAsStringSync(),
        )
        as Map<String, dynamic>;

void main() {
  test('parses golden W1 trace with four verified records', () {
    final trace = RunTrace.fromJson(_fixture('golden_w1.json'));

    expect(trace.workflowId, 'w1');
    expect(trace.status, 'COMPLETED');
    expect(trace.plan.steps, hasLength(4));
    expect(trace.records, hasLength(4));
    expect(trace.records.every((r) => r.verdict.passed), isTrue);
    expect(trace.voiceIntake, isNull);
    expect(trace.metrics.maskCentroidHitRate, 1.0);
    expect(trace.metrics.totalStepsCompleted, 4);
    expect(trace.initialMaskSet.masks.map((m) => m.maskId), [1, 2, 3, 4]);
  });

  test('parses golden W2 trace with voice intake', () {
    final trace = RunTrace.fromJson(_fixture('golden_w2.json'));

    expect(trace.workflowId, 'w2');
    expect(trace.voiceIntake, isNotNull);
    expect(trace.voiceIntake!.transcript.toLowerCase(), contains('anomaly'));
    expect(trace.records.length, greaterThanOrEqualTo(3));
    expect(trace.metrics.selfHealingRecoveries, greaterThanOrEqualTo(0));
  });

  test('golden steps carry zero raw coordinates', () {
    const forbidden = {
      'x',
      'y',
      'coords',
      'coordinates',
      'point',
      'click_x',
      'click_y',
      'raw_xy',
    };
    for (final name in ['golden_w1.json', 'golden_w2.json']) {
      final raw = _fixture(name);
      final plan = raw['plan'] as Map<String, dynamic>;
      for (final step in plan['steps'] as List) {
        final keys = (step as Map).keys.map((k) => k.toString()).toSet();
        expect(
          keys.intersection(forbidden),
          isEmpty,
          reason: '$name step emitted coordinates: $keys',
        );
      }
      final trace = RunTrace.fromJson(raw);
      for (final step in trace.plan.steps) {
        expect(step.targetMaskId, greaterThanOrEqualTo(1));
      }
    }
  });

  test('parses benchmark report payload', () {
    final report = BenchmarkReport.fromJson({
      'total_runs_analyzed': 28,
      'total_steps_executed': 122,
      'mean_mask_hit_rate': 1.0,
      'mean_verification_pass_rate': 0.93,
      'total_self_healing_recoveries': 12,
      'self_healing_success_rate': 1.0,
      'sam_latency_p50_ms': 0.03,
      'planner_latency_p50_ms': 0.04,
      'verifier_latency_p50_ms': 11.12,
      'workflows': {
        'w1': {
          'runs': 16,
          'steps_completed': '62/64',
          'mean_hit_rate': 1.0,
          'mean_pass_rate': 0.9688,
          'self_healing_events': 0,
        },
      },
    });

    expect(report.totalRunsAnalyzed, 28);
    expect(report.meanVerificationPassRate, closeTo(0.93, 1e-9));
    expect(report.workflows['w1']!.runs, 16);
    expect(report.workflows['w1']!.stepsCompleted, '62/64');
  });

  test('parses server status payloads', () {
    final health = HealthReport.fromJson({
      'passed': true,
      'execution_mode': 'simulated',
      'sam_model_id': 'meta-models/sam-3.1',
      'planner_model_id': 'meta-models/muse-spark',
      'verifier_model_id': 'meta-models/muse-spark-open-1026',
      'partner_provider': 'baseten',
      'display_dpi_scale': 2.0,
      'checks': {'mode_ready': true},
    });
    expect(health.passed, isTrue);
    expect(health.displayDpiScale, 2.0);
    expect(health.checks['mode_ready'], isTrue);

    final workflow = WorkflowInfo.fromJson({
      'workflow_id': 'w1',
      'title': 'W1',
      'description': 'Canvas',
    });
    expect(workflow.workflowId, 'w1');

    final summary = TraceSummary.fromJson({
      'trace_id': 'abc123',
      'workflow_id': 'w2',
      'status': 'COMPLETED',
      'created_at': '2026-10-31T00:00:00+00:00',
      'steps_completed': 3,
      'steps_planned': 3,
      'verification_pass_rate': 1.0,
      'self_healing_recoveries': 1,
    });
    expect(summary.selfHealingRecoveries, 1);
  });
}
