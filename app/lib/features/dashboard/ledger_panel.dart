// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Professional step-by-step autonomous cognition & verification ledger.
library;

import 'package:flutter/material.dart';

import '../../../models/trace.dart';
import '../../../theme/meta_theme.dart';
import '../../../widgets/section_card.dart';
import '../../../widgets/status_chip.dart';

/// Expandable audit log of every step attempt, actuation receipt, and visual verdict.
class LedgerPanel extends StatelessWidget {
  const LedgerPanel({required this.records, this.isLive = false, super.key});

  final List<StepExecutionRecord> records;
  final bool isLive;

  String _shortHash(String hash) =>
      hash.length > 12 ? '${hash.substring(0, 12)}…' : hash;

  String _capitalize(String value) =>
      value.isEmpty ? value : '${value[0].toUpperCase()}${value.substring(1)}';

  Widget _detailBlock(
    BuildContext context,
    String heading,
    List<(String, String)> rows,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          heading,
          style: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w700,
            color: MetaTheme.inkPrimary,
          ),
        ),
        const SizedBox(height: 6),
        ...rows.map(
          (row) => Padding(
            padding: const EdgeInsets.symmetric(vertical: 2.5),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox(
                  width: 140,
                  child: Text(
                    row.$1,
                    style: const TextStyle(
                      fontSize: 11,
                      color: MetaTheme.inkSecondary,
                    ),
                  ),
                ),
                Expanded(
                  child: Text(
                    row.$2,
                    style: const TextStyle(
                      fontSize: 11,
                      color: MetaTheme.inkPrimary,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    if (records.isEmpty) {
      if (isLive) {
        return SectionCard(
          title: 'Live verification ledger',
          icon: Icons.receipt_long,
          trailing: Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: MetaTheme.coralAlert.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(4),
              border: Border.all(color: MetaTheme.coralAlert),
            ),
            child: const Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                SizedBox(
                  width: 6,
                  height: 6,
                  child: CircularProgressIndicator(
                    strokeWidth: 1.5,
                    color: MetaTheme.coralAlert,
                  ),
                ),
                SizedBox(width: 5),
                Text(
                  'Live',
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: MetaTheme.coralAlert,
                  ),
                ),
              ],
            ),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 16),
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const SizedBox(
                    width: 28,
                    height: 28,
                    child: CircularProgressIndicator(
                      strokeWidth: 2.5,
                      color: MetaTheme.metaBlueDark,
                    ),
                  ),
                  const SizedBox(height: 14),
                  const Text(
                    'Analyzing the screen…',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: MetaTheme.inkPrimary,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Step records and verification verdicts appear here as each step completes.',
                    style: theme.textTheme.bodySmall,
                  ),
                ],
              ),
            ),
          ),
        );
      }
      return SectionCard(
        title: 'Verification ledger',
        icon: Icons.receipt_long,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 16),
          child: Center(
            child: Text(
              'No execution records yet. Run a workflow to generate some.',
              style: theme.textTheme.bodyMedium,
            ),
          ),
        ),
      );
    }

    return SectionCard(
      title: isLive
          ? 'Live verification ledger (${records.length} steps)'
          : 'Verification ledger (${records.length} steps)',
      icon: Icons.receipt_long,
      trailing: isLive
          ? Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: MetaTheme.coralAlert.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(4),
                border: Border.all(color: MetaTheme.coralAlert),
              ),
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  SizedBox(
                    width: 6,
                    height: 6,
                    child: CircularProgressIndicator(
                      strokeWidth: 1.5,
                      color: MetaTheme.coralAlert,
                    ),
                  ),
                  SizedBox(width: 5),
                  Text(
                    'Live',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      color: MetaTheme.coralAlert,
                    ),
                  ),
                ],
              ),
            )
          : null,
      child: Column(
        children: records.map((record) {
          final step = record.step;
          final receipt = record.receipt;
          final verdict = record.verdict;
          final passed = verdict.passed;

          return Card(
            margin: const EdgeInsets.only(bottom: 8),
            color: MetaTheme.surfaceCardElevated,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
              side: BorderSide(
                color: passed
                    ? MetaTheme.emeraldVerified.withValues(alpha: 0.25)
                    : MetaTheme.coralAlert.withValues(alpha: 0.3),
              ),
            ),
            child: ExpansionTile(
              initiallyExpanded: isLive,
              shape: const Border(),
              leading: Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: passed
                      ? MetaTheme.emeraldVerified.withValues(alpha: 0.15)
                      : MetaTheme.coralAlert.withValues(alpha: 0.15),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  passed ? Icons.check : Icons.close,
                  size: 16,
                  color: passed
                      ? MetaTheme.emeraldVerified
                      : MetaTheme.coralAlert,
                ),
              ),
              title: Row(
                children: [
                  Text(
                    'Step ${step.stepId} · ${_capitalize(step.operation)}',
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: MetaTheme.inkPrimary,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 6,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: MetaTheme.metaBlue.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      'Mask #${step.targetMaskId}',
                      style: const TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        color: MetaTheme.metaBlueDark,
                      ),
                    ),
                  ),
                  if (record.selfHealed) ...[
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 6,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: MetaTheme.emeraldVerified.withValues(
                          alpha: 0.15,
                        ),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: const Text(
                        'Self-healed',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          color: MetaTheme.emeraldVerified,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
              subtitle: Text(
                step.expectedOutcome.isNotEmpty
                    ? step.expectedOutcome
                    : step.reasoning,
                style: const TextStyle(
                  fontSize: 12,
                  color: MetaTheme.inkSecondary,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              trailing: StatusChip(
                passed ? 'Verified' : 'Failed',
                passed ? StatusKind.pass : StatusKind.fail,
              ),
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Divider(color: MetaTheme.surfaceCardBorder),
                      const SizedBox(height: 8),
                      _detailBlock(context, 'Actuation receipt', [
                        ('Target mask', '#${step.targetMaskId}'),
                        (
                          'Frame centroid',
                          '(${receipt.frameCentroidPx[0]}, ${receipt.frameCentroidPx[1]}) px',
                        ),
                        ('DPI scale', '${receipt.dpiScale}x'),
                        (
                          'OS point',
                          '(${receipt.osLogicalPoint[0]}, ${receipt.osLogicalPoint[1]})',
                        ),
                        if (step.dragToMaskId != null)
                          ('Drag destination', '#${step.dragToMaskId}'),
                        ('Pre-frame hash', _shortHash(receipt.preFrameHash)),
                        ('Post-frame hash', _shortHash(receipt.postFrameHash)),
                        (
                          'Actuation latency',
                          '${receipt.executionLatencyMs.toStringAsFixed(1)} ms',
                        ),
                      ]),
                      const SizedBox(height: 12),
                      _detailBlock(context, 'Verification', [
                        ('Verifier model', verdict.modelId),
                        ('Provider', verdict.partnerProvider),
                        ('Observed change', verdict.observedChange),
                        if (verdict.retryHint != null)
                          ('Retry hint', verdict.retryHint!),
                        (
                          'Verification latency',
                          '${verdict.latencyMs.toStringAsFixed(1)} ms',
                        ),
                      ]),
                    ],
                  ),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }
}
