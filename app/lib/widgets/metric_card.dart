// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Dense metric tile for the HUD metrics row.
library;

import 'package:flutter/material.dart';

import '../theme/meta_theme.dart';

/// Visual tone for a metric value.
enum MetricTone { neutral, good, warn, bad }

/// Single headline metric with a label, value, and caption.
class MetricCard extends StatelessWidget {
  const MetricCard({
    required this.label,
    required this.value,
    required this.caption,
    required this.icon,
    this.tone = MetricTone.neutral,
    super.key,
  });

  final String label;
  final String value;
  final String caption;
  final IconData icon;
  final MetricTone tone;

  Color _toneColor(BuildContext context) {
    switch (tone) {
      case MetricTone.good:
        return MetaTheme.green;
      case MetricTone.warn:
        return MetaTheme.amber;
      case MetricTone.bad:
        return MetaTheme.red;
      case MetricTone.neutral:
        return Theme.of(context).colorScheme.primary;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Row(
              children: [
                Icon(icon, size: 14, color: _toneColor(context)),
                const SizedBox(width: 5),
                Expanded(
                  child: Text(
                    label,
                    style: theme.textTheme.bodySmall?.copyWith(fontSize: 11),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 3),
            Text(
              value,
              style: theme.textTheme.titleMedium?.copyWith(
                color: _toneColor(context),
                fontWeight: FontWeight.w700,
                fontSize: 16,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 2),
            Text(
              caption,
              style: theme.textTheme.bodySmall?.copyWith(
                fontSize: 10,
                color: MetaTheme.inkSecondary,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }
}
