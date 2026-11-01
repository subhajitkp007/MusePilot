// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Compact status pill for health, verdicts, and run states.
library;

import 'package:flutter/material.dart';

import '../theme/meta_theme.dart';

/// Semantic status rendered as a colored pill.
enum StatusKind { pass, fail, warn, info, neutral }

/// Small rounded status indicator with a label.
class StatusChip extends StatelessWidget {
  const StatusChip(this.label, this.kind, {super.key});

  /// Green pass pill.
  const StatusChip.pass(String label, {Key? key})
    : this(label, StatusKind.pass, key: key);

  /// Red failure pill.
  const StatusChip.fail(String label, {Key? key})
    : this(label, StatusKind.fail, key: key);

  final String label;
  final StatusKind kind;

  (Color, Color) _colors(BuildContext context) {
    final onDark = Theme.of(context).brightness == Brightness.dark;
    switch (kind) {
      case StatusKind.pass:
        return (MetaTheme.green, Colors.white);
      case StatusKind.fail:
        return (MetaTheme.red, Colors.white);
      case StatusKind.warn:
        return (MetaTheme.amber, Colors.white);
      case StatusKind.info:
        return (onDark ? MetaTheme.blueDark : MetaTheme.blue, Colors.white);
      case StatusKind.neutral:
        return (
          onDark ? MetaTheme.darkSurface : MetaTheme.gray100,
          onDark ? MetaTheme.darkInk : MetaTheme.ink900,
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final (bg, fg) = _colors(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        label,
        style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: fg),
      ),
    );
  }
}
