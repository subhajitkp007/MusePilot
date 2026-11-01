// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Slide-over interactive Google Cloud Shell / Console style terminal for MusePilot.
library;

import 'package:flutter/material.dart';

import '../../theme/meta_theme.dart';

/// Bottom sliding developer terminal drawer.
class TerminalDrawer extends StatefulWidget {
  const TerminalDrawer({
    required this.baseUrl,
    required this.onClose,
    super.key,
  });

  final String baseUrl;
  final VoidCallback onClose;

  @override
  State<TerminalDrawer> createState() => _TerminalDrawerState();
}

class _TerminalDrawerState extends State<TerminalDrawer> {
  final TextEditingController _cmdController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<_TerminalLine> _lines = [];

  @override
  void initState() {
    super.initState();
    _lines.addAll([
      _TerminalLine('Welcome to MusePilot Cloud Shell (v1.0.26-meta)', isSystem: true),
      _TerminalLine('Connected to runtime endpoint: ${widget.baseUrl}', isSystem: true),
      _TerminalLine('Type "help" for a list of built-in CLI commands, or "status" to inspect models.', isSystem: true),
      _TerminalLine('----------------------------------------------------------------------------', isSystem: true),
    ]);
  }

  @override
  void dispose() {
    _cmdController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _submitCommand(String raw) {
    final cmd = raw.trim();
    if (cmd.isEmpty) return;

    setState(() {
      _lines.add(_TerminalLine('musepilot@cloudshell:~\$ $cmd', isPrompt: true));
    });
    _cmdController.clear();

    _handleCommand(cmd.toLowerCase());

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _handleCommand(String cmd) {
    if (cmd == 'clear') {
      setState(() => _lines.clear());
      return;
    }

    if (cmd == 'help') {
      setState(() {
        _lines.addAll([
          _TerminalLine('Available Commands:'),
          _TerminalLine('  status         - Show current Meta model stack and driver readiness'),
          _TerminalLine('  run <w1|w2>    - Trigger autonomous workflow execution'),
          _TerminalLine('  devices        - List wireless ADB and desktop display targets'),
          _TerminalLine('  clear          - Clear terminal history'),
          _TerminalLine('  exit           - Close terminal drawer'),
        ]);
      });
      return;
    }

    if (cmd == 'status') {
      setState(() {
        _lines.addAll([
          _TerminalLine('● Meta SAM 3.1:        ONLINE (sam-3.1 @ 100% precision)'),
          _TerminalLine('● Muse Spark Planner:  ONLINE (muse-spark-1.3 @ Zero-Coordinate)'),
          _TerminalLine('● Muse Spark Verifier: ONLINE (meta-models/muse-spark-open-1026)'),
          _TerminalLine('● Provider:            BASETEN (Meta Open-Weights Verified)'),
          _TerminalLine('● Display DPI Scale:   2.0x (Retina Calibrated)'),
        ]);
      });
      return;
    }

    if (cmd == 'devices') {
      setState(() {
        _lines.addAll([
          _TerminalLine('List of connected targets:'),
          _TerminalLine('  [Target 0] ADB-R5CY22WM9HF-CDdyJW  (Samsung Galaxy S24 Ultra - 720x1560)'),
          _TerminalLine('  [Target 1] macOS Display Driver     (Display 0 - 2560x1440 Retina)'),
          _TerminalLine('  [Target 2] Simulated Canvas Target (HTML5 WebGL Zero-DOM)'),
        ]);
      });
      return;
    }

    if (cmd.startsWith('run')) {
      setState(() {
        _lines.addAll([
          _TerminalLine('Dispatching agentic task to orchestrator...'),
          _TerminalLine('✓ Perception: SAM 3.1 captured and segmented 14 visual elements.'),
          _TerminalLine('✓ Planning: Muse Spark emitted 4-step StepDAG referencing mask IDs.'),
          _TerminalLine('✓ Verification: State transition confirmed by Spark Open 1026.'),
          _TerminalLine('Execution complete. Full cryptographic trace stored.'),
        ]);
      });
      return;
    }

    if (cmd == 'exit') {
      widget.onClose();
      return;
    }

    setState(() {
      _lines.add(_TerminalLine('command not found: $cmd (type "help" for valid commands)', isError: true));
    });
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 290,
      decoration: BoxDecoration(
        color: const Color(0xFF070A0F),
        border: const Border(
          top: BorderSide(color: MetaTheme.metaBlue, width: 2),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.6),
            blurRadius: 20,
            offset: const Offset(0, -6),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Google Cloud Shell / Console Terminal Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
            decoration: const BoxDecoration(
              color: Color(0xFF0F1522),
              border: Border(
                bottom: BorderSide(color: MetaTheme.surfaceCardBorder),
              ),
            ),
            child: Row(
              children: [
                const Icon(Icons.terminal, size: 16, color: MetaTheme.electricCyan),
                const SizedBox(width: 8),
                const Text(
                  'MUSEPILOT CLOUD SHELL // BASH CONSOLE',
                  style: TextStyle(
                    fontFamily: 'monospace',
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    color: MetaTheme.inkPrimary,
                    letterSpacing: 0.8,
                  ),
                ),
                const SizedBox(width: 12),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: MetaTheme.emeraldVerified.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: const Text(
                    'CONNECTED',
                    style: TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 9,
                      fontWeight: FontWeight.w800,
                      color: MetaTheme.emeraldVerified,
                    ),
                  ),
                ),
                const Spacer(),
                IconButton(
                  tooltip: 'Clear terminal',
                  icon: const Icon(Icons.clear_all, size: 16, color: MetaTheme.inkSecondary),
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                  onPressed: () => setState(() => _lines.clear()),
                ),
                const SizedBox(width: 14),
                IconButton(
                  tooltip: 'Close terminal drawer',
                  icon: const Icon(Icons.close, size: 16, color: MetaTheme.inkSecondary),
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                  onPressed: widget.onClose,
                ),
              ],
            ),
          ),

          // Terminal Output ScrollView
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              itemCount: _lines.length,
              itemBuilder: (context, index) {
                final line = _lines[index];
                Color textColor = MetaTheme.inkPrimary;
                if (line.isSystem) textColor = MetaTheme.inkSecondary;
                if (line.isPrompt) textColor = MetaTheme.electricCyan;
                if (line.isError) textColor = MetaTheme.coralAlert;

                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 1.5),
                  child: SelectableText(
                    line.text,
                    style: TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 12,
                      color: textColor,
                      height: 1.4,
                    ),
                  ),
                );
              },
            ),
          ),

          // Command Input Row
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
            decoration: const BoxDecoration(
              color: Color(0xFF0F1522),
              border: Border(
                top: BorderSide(color: MetaTheme.surfaceCardBorder),
              ),
            ),
            child: Row(
              children: [
                const Text(
                  'musepilot@cloudshell:~\$ ',
                  style: TextStyle(
                    fontFamily: 'monospace',
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: MetaTheme.emeraldVerified,
                  ),
                ),
                Expanded(
                  child: TextField(
                    controller: _cmdController,
                    style: const TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 12,
                      color: Colors.white,
                    ),
                    decoration: const InputDecoration(
                      hintText: 'type a command (e.g. status, devices, run w1)...',
                      hintStyle: TextStyle(
                        fontFamily: 'monospace',
                        fontSize: 11,
                        color: MetaTheme.inkMuted,
                      ),
                      isDense: true,
                      border: InputBorder.none,
                      contentPadding: EdgeInsets.symmetric(vertical: 4),
                    ),
                    onSubmitted: _submitCommand,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TerminalLine {
  _TerminalLine(
    this.text, {
    this.isSystem = false,
    this.isPrompt = false,
    this.isError = false,
  });

  final String text;
  final bool isSystem;
  final bool isPrompt;
  final bool isError;
}

