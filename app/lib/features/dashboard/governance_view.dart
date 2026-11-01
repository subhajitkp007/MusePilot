// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Governance, safety guardrails, and storage transparency view.
library;

import 'package:flutter/material.dart';

import '../../theme/meta_theme.dart';
import '../../widgets/section_card.dart';

/// Trust and safety controls, described as implemented.
class GovernanceView extends StatelessWidget {
  const GovernanceView({required this.verifierLabel, super.key});

  /// Short label for the active verifier (from server config).
  final String verifierLabel;

  Widget _policyCard({
    required IconData icon,
    required String title,
    required String status,
    required String description,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: MetaTheme.surfaceCardElevated,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: MetaTheme.surfaceCardBorder),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(icon, size: 20, color: color),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: MetaTheme.inkPrimary,
                      ),
                    ),
                    const Spacer(),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 6,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: color.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        status,
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          color: color,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  description,
                  style: const TextStyle(
                    fontSize: 12,
                    color: MetaTheme.inkSecondary,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SectionCard(
      title: 'Governance and safety',
      icon: Icons.shield,
      trailing: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: MetaTheme.emeraldVerified.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(6),
        ),
        child: const Text(
          'Auditable by design',
          style: TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w700,
            color: MetaTheme.emeraldVerified,
          ),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Zero-coordinate design note
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: MetaTheme.metaBlue.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: MetaTheme.metaBlue.withValues(alpha: 0.3),
              ),
            ),
            child: const Row(
              children: [
                Icon(
                  Icons.verified_outlined,
                  size: 28,
                  color: MetaTheme.metaBlueDark,
                ),
                SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Zero-coordinate design',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                          color: MetaTheme.metaBlueDark,
                        ),
                      ),
                      SizedBox(height: 2),
                      Text(
                        'Plans reference SAM 3.1 mask IDs, never raw screen coordinates. '
                        'The executor translates mask centroids to OS points with DPI scaling, '
                        'and every step is recorded with its receipt and verdict.',
                        style: TextStyle(
                          fontSize: 11,
                          color: MetaTheme.inkPrimary,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),

          // Safety policies
          _policyCard(
            icon: Icons.lock_outline,
            title: 'PII and secret redaction',
            status: 'Active',
            description:
                'Sensitive input values are redacted before ledger persistence; '
                'receipts carry redacted_input_value instead of raw text.',
            color: MetaTheme.emeraldVerified,
          ),
          const SizedBox(height: 8),

          _policyCard(
            icon: Icons.gavel,
            title: 'Destructive action gate',
            status: 'Flagged in plan',
            description:
                'The planner marks destructive steps, and the executor gates them behind '
                'require_destructive_confirmation. Rehearsal runs auto-confirm; '
                'disable auto-confirm to require operator sign-off.',
            color: MetaTheme.amberWarning,
          ),
          const SizedBox(height: 8),

          _policyCard(
            icon: Icons.memory,
            title: 'Local-first trace storage',
            status: 'On your server',
            description:
                'Frames, traces, and the audit ledger persist on your own server under the '
                'configured trace directory. Nothing is uploaded elsewhere by this app.',
            color: MetaTheme.metaBlueDark,
          ),
          const SizedBox(height: 8),

          _policyCard(
            icon: Icons.verified_user_outlined,
            title: 'Closed-loop verification',
            status: verifierLabel,
            description:
                'Every step transition is checked by the configured verifier before the run '
                'advances, and the verdict is stored with the step record.',
            color: MetaTheme.metaBlueDark,
          ),
        ],
      ),
    );
  }
}
