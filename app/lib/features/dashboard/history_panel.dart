// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Recent run history with one-tap trace loading.
library;

import 'package:flutter/material.dart';

import '../../../models/server.dart';
import '../../../theme/meta_theme.dart';
import '../../../widgets/section_card.dart';
import '../../../widgets/status_chip.dart';

/// Newest-first list of recorded runs.
class HistoryPanel extends StatelessWidget {
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
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    if (history.isEmpty) {
      return SectionCard(
        title: 'Run history',
        icon: Icons.history,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 20),
          child: Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.history_toggle_off,
                  size: 36,
                  color: MetaTheme.inkSecondary,
                ),
                const SizedBox(height: 10),
                const Text(
                  'No historical traces recorded yet.',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: MetaTheme.inkPrimary,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Completed and verified execution traces are automatically persisted to the local audit ledger.',
                  style: theme.textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ),
      );
    }
    return SectionCard(
      title: 'Run history (${history.length} traces)',
      icon: Icons.history,
      child: ListView.separated(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        itemCount: history.length,
        separatorBuilder: (_, _) => const Divider(height: 1),
        itemBuilder: (context, index) {
          final item = history[index];
          final active = item.traceId == activeTraceId;
          return ListTile(
            dense: true,
            selected: active,
            leading: StatusChip(item.workflowId.toUpperCase(), StatusKind.info),
            title: Text(
              item.traceId,
              style: theme.textTheme.bodyMedium?.copyWith(
                fontWeight: active ? FontWeight.w700 : FontWeight.w400,
              ),
            ),
            subtitle: Text(
              '${item.stepsCompleted}/${item.stepsPlanned} steps · '
              '${(item.verificationPassRate * 100).toStringAsFixed(1)}% verified'
              '${item.selfHealingRecoveries > 0 ? ' · ${item.selfHealingRecoveries} heals' : ''}',
            ),
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                StatusChip(
                  item.status == 'COMPLETED' ? 'Completed' : item.status,
                  item.status == 'COMPLETED'
                      ? StatusKind.pass
                      : StatusKind.warn,
                ),
                const Icon(Icons.chevron_right),
              ],
            ),
            onTap: () => onSelect(item.traceId),
          );
        },
      ),
    );
  }
}
