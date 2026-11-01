// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Target device driver selection view.
library;

import 'package:flutter/material.dart';

import '../../theme/meta_theme.dart';
import '../../widgets/section_card.dart';
import '../../widgets/status_chip.dart';

/// Driver selection cards for simulated, desktop, and ADB targets.
class FleetManagerView extends StatelessWidget {
  const FleetManagerView({
    required this.selectedDriver,
    required this.onSelectDriver,
    required this.adbAvailable,
    required this.executionMode,
    super.key,
  });

  final String selectedDriver;
  final ValueChanged<String> onSelectDriver;

  /// Whether the server currently sees an ADB device.
  final bool adbAvailable;

  /// Server execution mode (`live` or `simulated`).
  final String executionMode;

  Widget _driverCard({
    required String id,
    required String title,
    required String subtitle,
    required IconData icon,
    required String status,
    required StatusKind statusKind,
    required List<(String, String)> specs,
    required Color accentColor,
    String? note,
  }) {
    final isSelected = selectedDriver == id;

    return InkWell(
      onTap: () => onSelectDriver(id),
      borderRadius: BorderRadius.circular(10),
      child: Card(
        color: isSelected
            ? MetaTheme.surfaceCardElevated
            : MetaTheme.surfaceCard,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
          side: BorderSide(
            color: isSelected ? accentColor : MetaTheme.surfaceCardBorder,
            width: isSelected ? 1.5 : 1.0,
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: accentColor.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Icon(icon, size: 22, color: accentColor),
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
                                fontSize: 14,
                                fontWeight: FontWeight.w700,
                                color: MetaTheme.inkPrimary,
                              ),
                            ),
                            const SizedBox(width: 8),
                            StatusChip(status, statusKind),
                          ],
                        ),
                        Text(
                          subtitle,
                          style: const TextStyle(
                            fontSize: 12,
                            color: MetaTheme.inkSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Icon(
                    isSelected
                        ? Icons.check_circle
                        : Icons.radio_button_unchecked,
                    color: isSelected ? accentColor : MetaTheme.inkMuted,
                    size: 22,
                  ),
                ],
              ),
              const SizedBox(height: 12),
              const Divider(color: MetaTheme.surfaceCardBorder),
              const SizedBox(height: 10),
              Wrap(
                spacing: 14,
                runSpacing: 6,
                children: [for (final spec in specs) _spec(spec.$1, spec.$2)],
              ),
              if (note != null) ...[
                const SizedBox(height: 10),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: accentColor.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(
                      color: accentColor.withValues(alpha: 0.25),
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.info_outline, size: 14, color: accentColor),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          note,
                          style: const TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: MetaTheme.inkPrimary,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _spec(String label, String value) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          '$label: ',
          style: const TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w700,
            color: MetaTheme.inkMuted,
          ),
        ),
        Text(
          value,
          style: const TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w600,
            color: MetaTheme.inkPrimary,
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final adbOnline = adbAvailable;
    return SectionCard(
      title: 'Target devices',
      icon: Icons.devices,
      trailing: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: MetaTheme.emeraldVerified.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(6),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              adbOnline ? Icons.check_circle : Icons.info_outline,
              size: 12,
              color: adbOnline
                  ? MetaTheme.emeraldVerified
                  : MetaTheme.inkSecondary,
            ),
            const SizedBox(width: 5),
            Text(
              adbOnline ? '1 ADB device connected' : 'No ADB device',
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w700,
                color: adbOnline
                    ? MetaTheme.emeraldVerified
                    : MetaTheme.inkSecondary,
              ),
            ),
          ],
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Pick which target the agent perceives and controls. Device state is reported by the server.',
            style: TextStyle(fontSize: 13, color: MetaTheme.inkSecondary),
          ),
          const SizedBox(height: 14),

          // 1. Android over ADB
          _driverCard(
            id: 'adb',
            title: 'Android (ADB)',
            subtitle: adbOnline
                ? 'Device reachable from the server'
                : 'Connect a device to enable this target',
            icon: Icons.phone_android,
            status: adbOnline ? 'Connected' : 'Unavailable',
            statusKind: adbOnline ? StatusKind.pass : StatusKind.neutral,
            specs: const [
              ('Driver', 'adb'),
              ('Frames', 'Device screencap'),
              ('Input', 'adb shell input'),
            ],
            accentColor: MetaTheme.amberWarning,
            note: adbOnline ? null : 'Runs on this target fail until a device is connected to the server.',
          ),
          const SizedBox(height: 10),

          // 2. Desktop OS host
          _driverCard(
            id: 'desktop',
            title: 'Desktop',
            subtitle: 'Server-host screen and input',
            icon: Icons.desktop_windows,
            status: executionMode == 'live' ? 'Available' : 'Standby',
            statusKind: executionMode == 'live'
                ? StatusKind.pass
                : StatusKind.info,
            specs: const [
              ('Driver', 'desktop'),
              ('Frames', 'OS screen capture'),
              ('Input', 'OS dispatch'),
            ],
            accentColor: MetaTheme.metaBlueDark,
            note: executionMode == 'live'
                ? 'Real clicks require MUSEPILOT_ALLOW_LIVE_INPUT on the server.'
                : 'The server is in simulated mode; desktop runs stay virtual.',
          ),
          const SizedBox(height: 10),

          // 3. Simulated canvas sandbox
          _driverCard(
            id: 'simulated',
            title: 'Simulated canvas',
            subtitle: 'Hermetic in-memory test rig',
            icon: Icons.science,
            status: 'Available',
            statusKind: StatusKind.pass,
            specs: const [
              ('Driver', 'simulated'),
              ('Frames', 'In-memory pixels'),
              ('Input', 'Virtual'),
            ],
            accentColor: MetaTheme.metaBlueDark,
          ),
        ],
      ),
    );
  }
}
