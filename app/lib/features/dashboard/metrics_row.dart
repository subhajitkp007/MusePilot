// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Professional headline telemetry & performance KPI tiles for the active run.
library;

import 'package:flutter/material.dart';

import '../../../models/trace.dart';
import '../../../widgets/metric_card.dart';

/// Responsive grid of the 5 headline run metrics.
class MetricsRow extends StatelessWidget {
  const MetricsRow({
    required this.trace,
    required this.dpiScale,
    required this.verifierName,
    this.liveRecords,
    super.key,
  });

  final RunTrace? trace;
  final double dpiScale;

  /// Short label for the active verifier (from server config).
  final String verifierName;
  final List<StepExecutionRecord>? liveRecords;

  @override
  Widget build(BuildContext context) {
    final isLive = liveRecords != null;
    final liveList = liveRecords ?? const [];
    final liveTotal = liveList.length;
    final livePassed = liveList.where((r) => r.verdict.passed).length;
    final livePassRate = liveTotal > 0 ? (livePassed / liveTotal) * 100 : 0.0;
    final liveHeals = liveList.where((r) => r.selfHealed).length;

    final m = trace?.metrics;
    final passRate = isLive
        ? livePassRate
        : ((m?.verificationPassRate ?? 0) * 100);
    final latencyMs = m == null
        ? 0.0
        : (m.medianSamLatencyMs +
              m.medianPlannerLatencyMs +
              m.medianVerifierLatencyMs);
    final effectiveDpi = trace?.initialMaskSet.dpiScale ?? dpiScale;
    String pct(double v) => '${(v * 100).toStringAsFixed(1)}%';

    return LayoutBuilder(
      builder: (context, constraints) => GridView.count(
        crossAxisCount: constraints.maxWidth > 900 ? 5 : 2,
        mainAxisSpacing: 8,
        crossAxisSpacing: 8,
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        childAspectRatio: constraints.maxWidth > 900 ? 2.5 : 1.7,
        children: [
          MetricCard(
            label: 'Zero-coordinate invariant',
            value: isLive
                ? (liveTotal == 0 ? '--' : 'Enforced')
                : (m == null ? '--' : pct(m.maskCentroidHitRate)),
            caption: isLive
                ? '$liveTotal steps grounded'
                : 'Mask IDs only, no coordinates',
            icon: Icons.gps_fixed,
            tone: isLive
                ? (liveTotal == 0 ? MetricTone.neutral : MetricTone.good)
                : (m == null
                      ? MetricTone.neutral
                      : m.maskCentroidHitRate >= 1.0
                      ? MetricTone.good
                      : MetricTone.warn),
          ),
          MetricCard(
            label: verifierName,
            value: isLive
                ? (liveTotal == 0 ? '--' : '${passRate.toStringAsFixed(1)}%')
                : (m == null ? '--' : '${passRate.toStringAsFixed(1)}%'),
            caption: isLive
                ? '$livePassed of $liveTotal verified'
                : 'Verification pass rate',
            icon: Icons.verified,
            tone: isLive
                ? (liveTotal == 0
                      ? MetricTone.neutral
                      : (passRate >= 95 ? MetricTone.good : MetricTone.warn))
                : (m == null
                      ? MetricTone.neutral
                      : passRate >= 95
                      ? MetricTone.good
                      : MetricTone.warn),
          ),
          MetricCard(
            label: 'Mean action latency',
            value: m == null
                ? (isLive ? 'Measuring' : '--')
                : '${latencyMs.toStringAsFixed(0)}ms',
            caption: 'Perception + plan + actuate',
            icon: Icons.speed,
            tone: m == null
                ? MetricTone.neutral
                : latencyMs <= 1000
                ? MetricTone.good
                : MetricTone.warn,
          ),
          MetricCard(
            label: 'Self-heals',
            value: isLive
                ? '$liveHeals'
                : (m == null ? '--' : '${m.selfHealingRecoveries}'),
            caption: 'Obstructions recovered',
            icon: Icons.auto_fix_high,
            tone: (isLive ? liveHeals : (m?.selfHealingRecoveries ?? 0)) > 0
                ? MetricTone.good
                : MetricTone.neutral,
          ),
          MetricCard(
            label: 'Display calibration',
            value: '${effectiveDpi.toStringAsFixed(1)}x',
            caption: effectiveDpi == 1.0
                ? '1:1 physical pixels'
                : '${effectiveDpi.toStringAsFixed(1)}x DPI normalization',
            icon: Icons.aspect_ratio,
            tone: MetricTone.neutral,
          ),
        ],
      ),
    );
  }
}
