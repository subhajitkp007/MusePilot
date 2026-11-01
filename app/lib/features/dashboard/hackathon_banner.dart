// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Integration banner listing the configured Meta models and drivers.
library;

import 'package:flutter/material.dart';

import '../../theme/meta_theme.dart';

/// Top bar showing the Meta AI integrations behind this console.
class HackathonBanner extends StatelessWidget {
  const HackathonBanner({required this.verifierLabel, super.key});

  /// Short label for the active verifier (from server config).
  final String verifierLabel;

  Widget _pill({
    required IconData icon,
    required String title,
    required String badge,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 6),
          Text(
            title,
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: MetaTheme.inkPrimary,
            ),
          ),
          const SizedBox(width: 4),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.25),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text(
              badge,
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w700,
                color: color,
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: const BoxDecoration(
        color: MetaTheme.surfaceCard,
        border: Border(bottom: BorderSide(color: MetaTheme.surfaceCardBorder)),
      ),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: [
            Row(
              children: [
                const Icon(
                  Icons.stars,
                  color: MetaTheme.metaBlueDark,
                  size: 16,
                ),
                const SizedBox(width: 6),
                Text(
                  'Built with Meta AI',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    color: MetaTheme.metaBlueDark.withValues(alpha: 0.9),
                  ),
                ),
              ],
            ),
            const SizedBox(width: 16),
            _pill(
              icon: Icons.layers_outlined,
              title: 'Perception',
              badge: 'SAM 3.1',
              color: MetaTheme.metaBlueDark,
            ),
            const SizedBox(width: 8),
            _pill(
              icon: Icons.alt_route,
              title: 'Planner',
              badge: 'Muse Spark',
              color: MetaTheme.metaBlueDark,
            ),
            const SizedBox(width: 8),
            _pill(
              icon: Icons.verified_user,
              title: 'Verifier',
              badge: verifierLabel,
              color: MetaTheme.emeraldVerified,
            ),
            const SizedBox(width: 8),
            _pill(
              icon: Icons.healing,
              title: 'Self-healing',
              badge: 'Replan',
              color: MetaTheme.emeraldVerified,
            ),
            const SizedBox(width: 8),
            _pill(
              icon: Icons.phonelink,
              title: 'Targets',
              badge: 'Simulated · Desktop · ADB',
              color: MetaTheme.amberWarning,
            ),
          ],
        ),
      ),
    );
  }
}
