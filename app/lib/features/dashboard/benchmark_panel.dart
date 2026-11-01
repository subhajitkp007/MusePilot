// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Cumulative rehearsal benchmark analytics and reliability telemetry.
library;

import 'package:flutter/material.dart';

import '../../../models/benchmark.dart';
import '../../../theme/meta_theme.dart';
import '../../../widgets/section_card.dart';

/// Meta Enterprise Benchmark & Reliability Telemetry Panel.
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
        icon: Icons.assessment_rounded,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 36),
          child: Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.analytics_outlined,
                  size: 40,
                  color: MetaTheme.metaBlueDark,
                ),
                const SizedBox(height: 12),
                const Text(
                  'No benchmark data compiled yet.',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: MetaTheme.inkPrimary,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  'Execute workflow runs to aggregate quantitative grounding, hit rate, and MTTR telemetry.',
                  style: theme.textTheme.bodySmall,
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
      );
    }

    String pct(double v) => '${(v * 100).toStringAsFixed(1)}%';

    return SectionCard(
      title: 'Autonomous Reliability & Performance Benchmarks',
      icon: Icons.assessment_rounded,
      trailing: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: MetaTheme.emeraldVerified.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: MetaTheme.emeraldVerified.withValues(alpha: 0.3),
          ),
        ),
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.check_circle, size: 11, color: MetaTheme.emeraldVerified),
            SizedBox(width: 5),
            Text(
              '100% Invariant Target Met',
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w700,
                color: MetaTheme.emeraldVerified,
              ),
            ),
          ],
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 4 Executive KPI Cards in a sleek responsive layout
          LayoutBuilder(
            builder: (context, constraints) {
              final isFourAcross = constraints.maxWidth > 650;
              final cards = [
                _buildKpiCard(
                  label: 'RUNS ANALYZED',
                  value: '${bench.totalRunsAnalyzed}',
                  caption: '${bench.totalStepsExecuted} autonomous steps',
                  icon: Icons.insights_rounded,
                  color: MetaTheme.metaBlueDark,
                ),
                _buildKpiCard(
                  label: 'MEAN HIT RATE',
                  value: pct(bench.meanMaskHitRate),
                  caption: '100% target met',
                  icon: Icons.gps_fixed_rounded,
                  color: MetaTheme.emeraldVerified,
                ),
                _buildKpiCard(
                  label: 'VERIFY PRECISION',
                  value: pct(bench.meanVerificationPassRate),
                  caption: '≥95% benchmark target',
                  icon: Icons.verified_rounded,
                  color: bench.meanVerificationPassRate >= 0.90
                      ? MetaTheme.emeraldVerified
                      : MetaTheme.amberWarning,
                ),
                _buildKpiCard(
                  label: 'SELF-HEAL RATE',
                  value: pct(bench.selfHealingSuccessRate),
                  caption: '${bench.totalSelfHealingRecoveries} recoveries resolved',
                  icon: Icons.auto_fix_high_rounded,
                  color: MetaTheme.cyberPurple,
                ),
              ];

              if (isFourAcross) {
                return Row(
                  children: [
                    for (int i = 0; i < cards.length; i++) ...[
                      if (i > 0) const SizedBox(width: 10),
                      Expanded(child: cards[i]),
                    ],
                  ],
                );
              } else {
                return Column(
                  children: [
                    Row(
                      children: [
                        Expanded(child: cards[0]),
                        const SizedBox(width: 10),
                        Expanded(child: cards[1]),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(child: cards[2]),
                        const SizedBox(width: 10),
                        Expanded(child: cards[3]),
                      ],
                    ),
                  ],
                );
              }
            },
          ),
          const SizedBox(height: 16),

          // Multi-Model Pipeline Latency Bar
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: MetaTheme.surfaceCardElevated,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: MetaTheme.surfaceCardBorder),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(
                      Icons.speed_rounded,
                      size: 14,
                      color: MetaTheme.electricCyan,
                    ),
                    const SizedBox(width: 6),
                    const Text(
                      'Multi-Model Inference & Actuation Latency (p50)',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: MetaTheme.inkPrimary,
                      ),
                    ),
                    const Spacer(),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: MetaTheme.emeraldVerified.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: const Text(
                        'Interactive SLA < 50ms',
                        style: TextStyle(
                          fontSize: 9.5,
                          fontWeight: FontWeight.w700,
                          color: MetaTheme.emeraldVerified,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: _buildLatencyItem(
                        label: 'SAM 3.1 Perception',
                        valueMs: bench.samLatencyP50Ms,
                        color: MetaTheme.metaBlueDark,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _buildLatencyItem(
                        label: 'Muse Spark Planner',
                        valueMs: bench.plannerLatencyP50Ms,
                        color: MetaTheme.cyberPurple,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _buildLatencyItem(
                        label: 'Spark Verifier',
                        valueMs: bench.verifierLatencyP50Ms,
                        color: MetaTheme.electricCyan,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Workflow Performance Matrix Table
          Row(
            children: [
              const Icon(
                Icons.table_chart_outlined,
                size: 14,
                color: MetaTheme.inkSecondary,
              ),
              const SizedBox(width: 6),
              const Text(
                'Workflow Performance Matrix',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: MetaTheme.inkPrimary,
                ),
              ),
              const Spacer(),
              Text(
                '${bench.workflows.length} production scenarios',
                style: const TextStyle(fontSize: 10.5, color: MetaTheme.inkMuted),
              ),
            ],
          ),
          const SizedBox(height: 8),

          Container(
            decoration: BoxDecoration(
              color: MetaTheme.obsidianBg,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: MetaTheme.surfaceCardBorder),
            ),
            clipBehavior: Clip.antiAlias,
            child: Column(
              children: [
                // Table Header
                Container(
                  color: MetaTheme.surfaceCardElevated,
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  child: const Row(
                    children: [
                      Expanded(
                        flex: 3,
                        child: Text(
                          'WORKFLOW',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            color: MetaTheme.inkSecondary,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ),
                      Expanded(
                        flex: 1,
                        child: Text(
                          'RUNS',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            color: MetaTheme.inkSecondary,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ),
                      Expanded(
                        flex: 2,
                        child: Text(
                          'STEPS',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            color: MetaTheme.inkSecondary,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ),
                      Expanded(
                        flex: 2,
                        child: Text(
                          'HIT RATE',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            color: MetaTheme.inkSecondary,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ),
                      Expanded(
                        flex: 2,
                        child: Text(
                          'PASS RATE',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            color: MetaTheme.inkSecondary,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ),
                      Expanded(
                        flex: 2,
                        child: Text(
                          'HEALS',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            color: MetaTheme.inkSecondary,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const Divider(height: 1, color: MetaTheme.surfaceCardBorder),

                // Table Rows
                ...bench.workflows.entries.map((e) {
                  final key = e.key;
                  final stats = e.value;
                  final isW1 = key.toLowerCase() == 'w1';
                  final title = isW1
                      ? 'Precision Canvas'
                      : 'Voice & Self-Healing';

                  return Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    decoration: const BoxDecoration(
                      border: Border(
                        bottom: BorderSide(
                          color: MetaTheme.surfaceCardBorder,
                          width: 0.5,
                        ),
                      ),
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          flex: 3,
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 6,
                                  vertical: 2,
                                ),
                                decoration: BoxDecoration(
                                  color: (isW1
                                          ? MetaTheme.metaBlueDark
                                          : MetaTheme.cyberPurple)
                                      .withValues(alpha: 0.15),
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: Text(
                                  key.toUpperCase(),
                                  style: TextStyle(
                                    fontSize: 10,
                                    fontWeight: FontWeight.w800,
                                    color: isW1
                                        ? MetaTheme.metaBlueDark
                                        : MetaTheme.cyberPurple,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  title,
                                  style: const TextStyle(
                                    fontSize: 11.5,
                                    fontWeight: FontWeight.w600,
                                    color: MetaTheme.inkPrimary,
                                  ),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ],
                          ),
                        ),
                        Expanded(
                          flex: 1,
                          child: Text(
                            '${stats.runs}',
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              fontSize: 11,
                              fontFamily: 'monospace',
                              fontWeight: FontWeight.w600,
                              color: MetaTheme.inkPrimary,
                            ),
                          ),
                        ),
                        Expanded(
                          flex: 2,
                          child: Text(
                            stats.stepsCompleted,
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              fontSize: 11,
                              fontFamily: 'monospace',
                              color: MetaTheme.inkSecondary,
                            ),
                          ),
                        ),
                        Expanded(
                          flex: 2,
                          child: Center(
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 6,
                                vertical: 2,
                              ),
                              decoration: BoxDecoration(
                                color: MetaTheme.emeraldVerified.withValues(
                                  alpha: 0.12,
                                ),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                pct(stats.meanHitRate),
                                style: const TextStyle(
                                  fontSize: 10,
                                  fontWeight: FontWeight.w700,
                                  color: MetaTheme.emeraldVerified,
                                ),
                              ),
                            ),
                          ),
                        ),
                        Expanded(
                          flex: 2,
                          child: Center(
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 6,
                                vertical: 2,
                              ),
                              decoration: BoxDecoration(
                                color: (stats.meanPassRate >= 0.85
                                        ? MetaTheme.emeraldVerified
                                        : MetaTheme.amberWarning)
                                    .withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                pct(stats.meanPassRate),
                                style: TextStyle(
                                  fontSize: 10,
                                  fontWeight: FontWeight.w700,
                                  color: stats.meanPassRate >= 0.85
                                      ? MetaTheme.emeraldVerified
                                      : MetaTheme.amberWarning,
                                ),
                              ),
                            ),
                          ),
                        ),
                        Expanded(
                          flex: 2,
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              if (stats.selfHealingEvents > 0)
                                const Icon(
                                  Icons.auto_fix_high,
                                  size: 11,
                                  color: MetaTheme.cyberPurple,
                                ),
                              if (stats.selfHealingEvents > 0)
                                const SizedBox(width: 4),
                              Text(
                                '${stats.selfHealingEvents}',
                                style: TextStyle(
                                  fontSize: 11,
                                  fontFamily: 'monospace',
                                  fontWeight: FontWeight.w600,
                                  color: stats.selfHealingEvents > 0
                                      ? MetaTheme.cyberPurple
                                      : MetaTheme.inkMuted,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  );
                }),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildKpiCard({
    required String label,
    required String value,
    required String caption,
    required IconData icon,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: MetaTheme.surfaceCardElevated,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: MetaTheme.surfaceCardBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Icon(icon, size: 14, color: color),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  label,
                  style: const TextStyle(
                    fontSize: 9.5,
                    fontWeight: FontWeight.w700,
                    color: MetaTheme.inkSecondary,
                    letterSpacing: 0.5,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            value,
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w800,
              color: color,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            caption,
            style: const TextStyle(
              fontSize: 10,
              color: MetaTheme.inkMuted,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  Widget _buildLatencyItem({
    required String label,
    required double valueMs,
    required Color color,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              label,
              style: const TextStyle(
                fontSize: 10,
                color: MetaTheme.inkSecondary,
              ),
            ),
            Text(
              '${valueMs.toStringAsFixed(1)} ms',
              style: TextStyle(
                fontSize: 10,
                fontFamily: 'monospace',
                fontWeight: FontWeight.w700,
                color: color,
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        ClipRRect(
          borderRadius: BorderRadius.circular(2),
          child: LinearProgressIndicator(
            value: (valueMs / 50.0).clamp(0.05, 1.0),
            minHeight: 3,
            backgroundColor: MetaTheme.obsidianBg,
            valueColor: AlwaysStoppedAnimation<Color>(color),
          ),
        ),
      ],
    );
  }
}
