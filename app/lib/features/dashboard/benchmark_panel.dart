// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Cumulative rehearsal benchmark analytics (Milestone M9).
library;

import 'package:flutter/material.dart';

import '../../../models/benchmark.dart';
import '../../../theme/meta_theme.dart';
import '../../../widgets/metric_card.dart';
import '../../../widgets/section_card.dart';

/// Benchmark headline tiles plus a per-workflow breakdown table.
class BenchmarkPanel extends StatelessWidget {
  const BenchmarkPanel({required this.report, super.key});

  final BenchmarkReport? report;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final bench = report;
    if (bench == null) {
      return SectionCard(
        title: 'Autonomous Reliability & Performance Benchmarks',
        icon: Icons.assessment,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 20),
          child: Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.analytics_outlined,
                  size: 36,
                  color: MetaTheme.metaBlueDark,
                ),
                const SizedBox(height: 10),
                const Text(
                  'No benchmark data compiled yet.',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: MetaTheme.inkPrimary,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Execute workflow runs to aggregate quantitative grounding, hit rate, and MTTR telemetry.',
                  style: theme.textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ),
      );
    }
    String pct(double v) => '${(v * 100).toStringAsFixed(1)}%';
    final rows = bench.workflows.entries
        .map(
          (e) => DataRow(
            cells: [
              DataCell(
                Text(
                  e.key.toUpperCase(),
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
              ),
              DataCell(Text('${e.value.runs}')),
              DataCell(Text(e.value.stepsCompleted)),
              DataCell(Text(pct(e.value.meanHitRate))),
              DataCell(Text(pct(e.value.meanPassRate))),
              DataCell(Text('${e.value.selfHealingEvents}')),
            ],
          ),
        )
        .toList();
    return SectionCard(
      title: 'Autonomous Reliability & Performance Benchmarks',
      icon: Icons.assessment,
      child: Column(
        children: [
          LayoutBuilder(
            builder: (context, constraints) => GridView.count(
              crossAxisCount: constraints.maxWidth > 900 ? 4 : 2,
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              childAspectRatio: 1.6,
              children: [
                MetricCard(
                  label: 'Runs analyzed',
                  value: '${bench.totalRunsAnalyzed}',
                  caption: '${bench.totalStepsExecuted} steps',
                  icon: Icons.history,
                ),
                MetricCard(
                  label: 'Mean hit rate',
                  value: pct(bench.meanMaskHitRate),
                  caption: '100% target',
                  icon: Icons.gps_fixed,
                  tone: bench.meanMaskHitRate >= 1.0
                      ? MetricTone.good
                      : MetricTone.warn,
                ),
                MetricCard(
                  label: 'Verify precision',
                  value: pct(bench.meanVerificationPassRate),
                  caption: '≥95% target',
                  icon: Icons.verified,
                  tone: bench.meanVerificationPassRate >= 0.95
                      ? MetricTone.good
                      : MetricTone.warn,
                ),
                MetricCard(
                  label: 'Self-heal rate',
                  value: pct(bench.selfHealingSuccessRate),
                  caption: '${bench.totalSelfHealingRecoveries} recoveries',
                  icon: Icons.healing,
                  tone: MetricTone.good,
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: DataTable(
              columns: const [
                DataColumn(label: Text('Workflow')),
                DataColumn(label: Text('Runs'), numeric: true),
                DataColumn(label: Text('Steps')),
                DataColumn(label: Text('Hit'), numeric: true),
                DataColumn(label: Text('Pass'), numeric: true),
                DataColumn(label: Text('Heals'), numeric: true),
              ],
              rows: rows,
            ),
          ),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerLeft,
            child: Text(
              'p50 latency — SAM ${bench.samLatencyP50Ms.toStringAsFixed(2)} ms · '
              'Planner ${bench.plannerLatencyP50Ms.toStringAsFixed(2)} ms · '
              'Verifier ${bench.verifierLatencyP50Ms.toStringAsFixed(2)} ms',
              style: theme.textTheme.bodySmall,
            ),
          ),
        ],
      ),
    );
  }
}
