// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Server connection bar with editable API base URL and health status.
library;

import 'package:flutter/material.dart';

import '../../../models/server.dart';
import '../../../theme/meta_theme.dart';
import '../../../widgets/section_card.dart';
import '../../../widgets/status_chip.dart';

/// Edits the API base URL (for phones and remote servers) and shows health.
class ConnectionBar extends StatefulWidget {
  const ConnectionBar({
    required this.baseUrl,
    required this.health,
    required this.refreshing,
    required this.onApply,
    required this.onRefresh,
    this.config,
    super.key,
  });

  final String baseUrl;
  final HealthReport? health;
  final ServerConfig? config;
  final bool refreshing;
  final ValueChanged<String> onApply;
  final VoidCallback onRefresh;

  @override
  State<ConnectionBar> createState() => _ConnectionBarState();
}

class _ConnectionBarState extends State<ConnectionBar> {
  late final TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.baseUrl);
  }

  @override
  void didUpdateWidget(ConnectionBar oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.baseUrl != widget.baseUrl &&
        _controller.text != widget.baseUrl) {
      _controller.text = widget.baseUrl;
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final health = widget.health;
    return SectionCard(
      title: 'Server connection',
      icon: Icons.hub,
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(
            tooltip: 'Refresh status',
            icon: widget.refreshing
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.refresh, size: 18),
            onPressed: widget.refreshing ? null : widget.onRefresh,
          ),
          const SizedBox(width: 4),
          if (health == null)
            const StatusChip('Connecting', StatusKind.neutral)
          else if (health.passed)
            const StatusChip('Connected', StatusKind.pass)
          else
            const StatusChip('Degraded', StatusKind.warn),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _controller,
                  decoration: const InputDecoration(
                    labelText: 'Server URL',
                    hintText: 'http://localhost:8501',
                    prefixIcon: Icon(
                      Icons.dns,
                      size: 18,
                      color: MetaTheme.metaBlueDark,
                    ),
                  ),
                  onSubmitted: widget.onApply,
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton.icon(
                icon: const Icon(Icons.link, size: 16),
                label: const Text('Connect'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: MetaTheme.surfaceCardElevated,
                  foregroundColor: MetaTheme.inkPrimary,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                    side: const BorderSide(color: MetaTheme.surfaceCardBorder),
                  ),
                ),
                onPressed: () => widget.onApply(_controller.text),
              ),
            ],
          ),
          if (health != null) ...[
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: [
                _chip('SAM: ${health.samModelId}', MetaTheme.metaBlueDark),
                _chip(
                  'Planner: ${health.plannerModelId}',
                  MetaTheme.metaBlueDark,
                ),
                _chip(
                  'Verifier: ${widget.config?.verifierDisplayName ?? health.verifierModelId}',
                  MetaTheme.emeraldVerified,
                ),
                _chip(
                  'Provider: ${health.partnerProvider}',
                  MetaTheme.inkSecondary,
                ),
                _chip(
                  'DPI scale: ${health.displayDpiScale}x',
                  MetaTheme.amberWarning,
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _chip(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 10,
          fontWeight: FontWeight.w600,
          color: color,
        ),
      ),
    );
  }
}
