// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Recent run history with filters and one-tap trace loading into Mission Control.
library;

import 'package:flutter/material.dart';

import '../../../models/server.dart';
import '../../../theme/meta_theme.dart';
import '../../../widgets/section_card.dart';

/// Newest-first list of recorded runs with status filtering.
class HistoryPanel extends StatefulWidget {
  const HistoryPanel({
    required this.history,
    required this.activeTraceId,
    required this.onSelect,
    super.key,
  });

  final List<TraceSummary> history;
  final String? activeTraceId;
  final ValueChanged<String> onSelect;

  @override
  State<HistoryPanel> createState() => _HistoryPanelState();
}

class _HistoryPanelState extends State<HistoryPanel> {
  String _activeFilter = 'all'; // all, completed, healed, escalated

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final history = widget.history;

    if (history.isEmpty) {
      return SectionCard(
        title: 'Run history',
        icon: Icons.history_rounded,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 36),
          child: Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.history_toggle_off_rounded,
                  size: 40,
                  color: MetaTheme.inkSecondary,
                ),
                const SizedBox(height: 12),
                const Text(
                  'No historical traces recorded yet.',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: MetaTheme.inkPrimary,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  'Completed and verified execution traces are automatically persisted to the local audit ledger.',
                  style: theme.textTheme.bodySmall,
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
      );
    }

    // Filter traces
    final filtered = history.where((t) {
      if (_activeFilter == 'completed') return t.status == 'COMPLETED';
      if (_activeFilter == 'healed') return t.selfHealingRecoveries > 0;
      if (_activeFilter == 'escalated') return t.status != 'COMPLETED';
      return true;
    }).toList();

    final completedCount = history.where((t) => t.status == 'COMPLETED').length;
    final healedCount = history.where((t) => t.selfHealingRecoveries > 0).length;

    return SectionCard(
      title: 'Run history',
      icon: Icons.history_rounded,
      trailing: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: MetaTheme.surfaceCardElevated,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: MetaTheme.surfaceCardBorder),
        ),
        child: Text(
          '${history.length} traces logged',
          style: const TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w700,
            color: MetaTheme.inkSecondary,
          ),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Filter Tabs
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                _buildFilterChip('all', 'All (${history.length})'),
                const SizedBox(width: 6),
                _buildFilterChip('completed', 'Completed ($completedCount)'),
                const SizedBox(width: 6),
                _buildFilterChip('healed', 'Recovered ($healedCount)'),
                const SizedBox(width: 6),
                _buildFilterChip(
                  'escalated',
                  'Escalated (${history.length - completedCount})',
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),

          // Trace list
          if (filtered.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 24),
              child: Center(
                child: Text(
                  'No traces match the active filter.',
                  style: theme.textTheme.bodySmall,
                ),
              ),
            )
          else
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: filtered.length,
              separatorBuilder: (_, _) => const SizedBox(height: 6),
              itemBuilder: (context, index) {
                final item = filtered[index];
                final isSelected = item.traceId == widget.activeTraceId;
                final isW1 = item.workflowId.toLowerCase() == 'w1';
                final isCompleted = item.status == 'COMPLETED';
                final hasHealed = item.selfHealingRecoveries > 0;

                final workflowTitle = isW1
                    ? 'Precision Canvas'
                    : 'Voice Incident';

                final shortId = item.traceId.length > 8
                    ? item.traceId.substring(0, 8)
                    : item.traceId;

                return InkWell(
                  onTap: () => widget.onSelect(item.traceId),
                  borderRadius: BorderRadius.circular(8),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 150),
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                    decoration: BoxDecoration(
                      color: isSelected
                          ? MetaTheme.metaBlue.withValues(alpha: 0.12)
                          : MetaTheme.surfaceCardElevated,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: isSelected
                            ? MetaTheme.metaBlueDark
                            : MetaTheme.surfaceCardBorder,
                        width: isSelected ? 1.5 : 1.0,
                      ),
                    ),
                    child: Row(
                      children: [
                        // Workflow Badge
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 6,
                            vertical: 3,
                          ),
                          decoration: BoxDecoration(
                            color: (isW1
                                    ? MetaTheme.metaBlueDark
                                    : MetaTheme.cyberPurple)
                                .withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            item.workflowId.toUpperCase(),
                            style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w800,
                              color: isW1
                                  ? MetaTheme.metaBlueDark
                                  : MetaTheme.cyberPurple,
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),

                        // Title & Metadata
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Text(
                                    workflowTitle,
                                    style: TextStyle(
                                      fontSize: 12,
                                      fontWeight: isSelected
                                          ? FontWeight.w700
                                          : FontWeight.w600,
                                      color: MetaTheme.inkPrimary,
                                    ),
                                  ),
                                  const SizedBox(width: 6),
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 4,
                                      vertical: 1,
                                    ),
                                    decoration: BoxDecoration(
                                      color: MetaTheme.obsidianBg,
                                      borderRadius: BorderRadius.circular(3),
                                    ),
                                    child: Text(
                                      '#$shortId',
                                      style: const TextStyle(
                                        fontSize: 9.5,
                                        fontFamily: 'monospace',
                                        color: MetaTheme.inkMuted,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 3),
                              Row(
                                children: [
                                  Text(
                                    '${item.stepsCompleted}/${item.stepsPlanned} steps',
                                    style: const TextStyle(
                                      fontSize: 10.5,
                                      color: MetaTheme.inkSecondary,
                                    ),
                                  ),
                                  const Text(
                                    ' · ',
                                    style: TextStyle(
                                      fontSize: 10,
                                      color: MetaTheme.inkMuted,
                                    ),
                                  ),
                                  Text(
                                    '${(item.verificationPassRate * 100).toInt()}% verified',
                                    style: TextStyle(
                                      fontSize: 10.5,
                                      fontWeight: FontWeight.w600,
                                      color: item.verificationPassRate >= 0.8
                                          ? MetaTheme.emeraldVerified
                                          : MetaTheme.amberWarning,
                                    ),
                                  ),
                                  if (hasHealed) ...[
                                    const Text(
                                      ' · ',
                                      style: TextStyle(
                                        fontSize: 10,
                                        color: MetaTheme.inkMuted,
                                      ),
                                    ),
                                    const Icon(
                                      Icons.auto_fix_high,
                                      size: 10,
                                      color: MetaTheme.cyberPurple,
                                    ),
                                    const SizedBox(width: 2),
                                    Text(
                                      '${item.selfHealingRecoveries} healed',
                                      style: const TextStyle(
                                        fontSize: 10,
                                        fontWeight: FontWeight.w600,
                                        color: MetaTheme.cyberPurple,
                                      ),
                                    ),
                                  ],
                                ],
                              ),
                            ],
                          ),
                        ),

                        // Status Chip
                        _buildStatusChip(
                          isCompleted: isCompleted,
                          hasHealed: hasHealed,
                          status: item.status,
                        ),
                        const SizedBox(width: 4),
                        const Icon(
                          Icons.chevron_right,
                          size: 14,
                          color: MetaTheme.inkMuted,
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
        ],
      ),
    );
  }

  Widget _buildFilterChip(String key, String label) {
    final active = _activeFilter == key;
    return InkWell(
      onTap: () => setState(() => _activeFilter = key),
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: active ? MetaTheme.metaBlue : MetaTheme.surfaceCardElevated,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: active ? MetaTheme.metaBlueDark : MetaTheme.surfaceCardBorder,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 10,
            fontWeight: active ? FontWeight.w700 : FontWeight.w500,
            color: active ? Colors.white : MetaTheme.inkSecondary,
          ),
        ),
      ),
    );
  }

  Widget _buildStatusChip({
    required bool isCompleted,
    required bool hasHealed,
    required String status,
  }) {
    if (isCompleted) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
        decoration: BoxDecoration(
          color: MetaTheme.emeraldVerified.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: MetaTheme.emeraldVerified.withValues(alpha: 0.3),
          ),
        ),
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.check, size: 10, color: MetaTheme.emeraldVerified),
            SizedBox(width: 3),
            Text(
              'Completed',
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w700,
                color: MetaTheme.emeraldVerified,
              ),
            ),
          ],
        ),
      );
    }

    if (hasHealed) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
        decoration: BoxDecoration(
          color: MetaTheme.cyberPurple.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: MetaTheme.cyberPurple.withValues(alpha: 0.3),
          ),
        ),
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.auto_fix_high, size: 10, color: MetaTheme.cyberPurple),
            SizedBox(width: 3),
            Text(
              'Recovered',
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w700,
                color: MetaTheme.cyberPurple,
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: MetaTheme.amberWarning.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: MetaTheme.amberWarning.withValues(alpha: 0.3),
        ),
      ),
      child: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.shield_outlined, size: 10, color: MetaTheme.amberWarning),
          SizedBox(width: 3),
          Text(
            'Escalated',
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w700,
              color: MetaTheme.amberWarning,
            ),
          ),
        ],
      ),
    );
  }
}
