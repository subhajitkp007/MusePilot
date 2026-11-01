// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Run configuration panel: workflow, target, intent, and live telemetry.
library;

import 'dart:async';

import 'package:flutter/material.dart';

import '../../../core/api_client.dart';
import '../../../core/voice_recorder.dart';
import '../../../models/server.dart';
import '../../../models/trace.dart';
import '../../../theme/meta_theme.dart';
import '../../../widgets/section_card.dart';
import '../../../widgets/status_chip.dart';

/// Execution controller: pick a workflow and target, edit intent, run.
class RunPanel extends StatefulWidget {
  const RunPanel({
    required this.workflows,
    required this.selectedWorkflow,
    required this.onSelectWorkflow,
    required this.injectModal,
    required this.onInjectModal,
    required this.driver,
    required this.onSelectDriver,
    required this.intentController,
    required this.running,
    required this.onRun,
    required this.spans,
    required this.trace,
    required this.baseUrl,
    required this.adbAvailable,
    required this.api,
    this.voiceRecorder,
    super.key,
  });

  final List<WorkflowInfo> workflows;
  final String selectedWorkflow;
  final ValueChanged<String> onSelectWorkflow;
  final bool injectModal;
  final ValueChanged<bool> onInjectModal;
  final String driver;
  final ValueChanged<String> onSelectDriver;
  final TextEditingController intentController;
  final bool running;
  final VoidCallback onRun;
  final List<Map<String, dynamic>> spans;
  final RunTrace? trace;

  /// API base URL, shown in the voice-transcription guidance.
  final String baseUrl;

  /// Whether the server currently sees an ADB device.
  final bool adbAvailable;

  /// API client used for voice transcription uploads.
  final MusePilotApi api;

  /// Recorder override for tests; defaults to the platform recorder.
  final VoiceRecorder? voiceRecorder;

  @override
  State<RunPanel> createState() => _RunPanelState();
}

class _RunPanelState extends State<RunPanel> {
  static const int _maxRecordingSeconds = 60;

  VoiceRecorder? _recorder;

  /// Test override when provided, otherwise the lazily created platform
  /// recorder (lazy so widget tests never touch platform channels).
  VoiceRecorder get _effectiveRecorder =>
      widget.voiceRecorder ?? (_recorder ??= PlatformVoiceRecorder());
  bool _recording = false;
  bool _transcribing = false;
  int _elapsedSeconds = 0;
  Timer? _elapsedTimer;
  List<String> get _quickPrompts {
    if (widget.driver == 'adb') {
      return const [
        'Set alarm for 9:00 AM on Clock app',
        'Open Clock app and toggle Sunday alarms',
        'Open Settings and check Battery status',
        'Open Calculator and compute 245 * 18',
      ];
    }
    if (widget.driver == 'desktop') {
      return const [
        'Open Terminal and check git status',
        'Toggle System Dark Mode in Settings',
        'Open Browser and inspect dashboard',
        'Reconcile invoice #4029 in SAP inventory terminal',
      ];
    }
    return const [
      'Calibrate frequency slider to 75% and toggle damping',
      'Dismiss blocking modal, replan, and resume triage',
      'Set gain calibration to +12dB and verify',
      'Run precision grounding check on the canvas',
    ];
  }

  void _applyQuickPrompt(String prompt) {
    if (widget.running) return;
    widget.intentController.text = prompt;
    setState(() {});
  }

  @override
  void dispose() {
    _elapsedTimer?.cancel();
    _recorder?.dispose();
    super.dispose();
  }

  void _snack(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(message)));
  }

  /// Manual fallback when the mic is unavailable: transcribe via curl.
  void _showVoiceGuidance(String reason) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Voice input unavailable'),
        content: Text(
          '$reason\n\nRecord a WAV clip in any app, then transcribe it:\n\n'
          'curl -X POST ${widget.baseUrl}/api/voice/transcribe \\\n'
          '  -F "audio=@command.wav" -F "workflow_id=w2"\n\n'
          'Paste the returned transcript into the instruction box and run. '
          'See the SDK Hub tab for more examples.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Got it'),
          ),
        ],
      ),
    );
  }

  String get _elapsedLabel {
    final minutes = _elapsedSeconds ~/ 60;
    final seconds = _elapsedSeconds % 60;
    return '$minutes:${seconds.toString().padLeft(2, '0')}';
  }

  /// Starts recording, or stops and transcribes when already recording.
  Future<void> _toggleRecording() async {
    if (widget.running || _transcribing) return;
    if (_recording) {
      await _stopAndTranscribe();
      return;
    }
    if (!_effectiveRecorder.isSupported) {
      _showVoiceGuidance(
        'This platform cannot capture microphone audio directly.',
      );
      return;
    }
    bool allowed;
    try {
      allowed = await _effectiveRecorder.hasPermission();
    } on Exception {
      _showVoiceGuidance('Microphone permission could not be requested.');
      return;
    }
    if (!allowed) {
      _showVoiceGuidance(
        'Microphone permission was denied. Enable it in system settings, '
        'or transcribe manually below.',
      );
      return;
    }
    try {
      await _effectiveRecorder.start();
    } on Exception catch (e) {
      _snack('Could not start recording ($e).');
      return;
    }
    setState(() {
      _recording = true;
      _elapsedSeconds = 0;
    });
    _elapsedTimer?.cancel();
    _elapsedTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      if (_elapsedSeconds + 1 >= _maxRecordingSeconds) {
        _stopAndTranscribe();
        return;
      }
      setState(() => _elapsedSeconds += 1);
    });
  }

  /// Stops the mic, uploads the WAV, and fills the intent with the transcript.
  Future<void> _stopAndTranscribe() async {
    if (!_recording) return;
    _elapsedTimer?.cancel();
    setState(() {
      _recording = false;
      _transcribing = true;
    });
    try {
      final bytes = await _effectiveRecorder.stop();
      if (bytes == null || bytes.isEmpty) {
        _snack('No audio captured. Try recording again.');
        return;
      }
      final transcript = await widget.api.transcribeAudio(
        audioBytes: bytes,
        workflowId: widget.selectedWorkflow,
      );
      if (!mounted) return;
      setState(() {
        widget.intentController.text = transcript.transcript;
      });
      _snack(
        'Transcript ready '
        '(${(transcript.confidence * 100).toStringAsFixed(0)}% confidence).',
      );
    } on ApiException catch (e) {
      _snack('Transcription failed: ${e.message}');
    } on Exception catch (e) {
      _snack('Transcription failed ($e).');
    } finally {
      if (mounted) setState(() => _transcribing = false);
    }
  }

  /// Voice button reflecting idle, recording, and transcribing states.
  Widget _voiceButton() {
    final disabled = widget.running || _transcribing;
    if (_transcribing) {
      return TextButton.icon(
        icon: const SizedBox(
          width: 14,
          height: 14,
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
        label: const Text(
          'Transcribing…',
          style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
        ),
        style: TextButton.styleFrom(
          foregroundColor: MetaTheme.inkSecondary,
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        ),
        onPressed: null,
      );
    }
    if (_recording) {
      return TextButton.icon(
        icon: Container(
          width: 10,
          height: 10,
          decoration: const BoxDecoration(
            color: MetaTheme.coralAlert,
            shape: BoxShape.circle,
          ),
        ),
        label: Text(
          'Stop · $_elapsedLabel',
          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
        ),
        style: TextButton.styleFrom(
          foregroundColor: MetaTheme.coralAlert,
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        ),
        onPressed: _toggleRecording,
      );
    }
    return TextButton.icon(
      icon: const Icon(Icons.mic_none, size: 16),
      label: const Text(
        'Voice input',
        style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
      ),
      style: TextButton.styleFrom(
        foregroundColor: MetaTheme.inkSecondary,
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      ),
      onPressed: disabled ? null : _toggleRecording,
    );
  }

  Widget _targetCard({
    required IconData icon,
    required String title,
    required String subtitle,
    required Color accent,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: MetaTheme.surfaceCardElevated,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: MetaTheme.surfaceCardBorder),
      ),
      child: Row(
        children: [
          Icon(icon, size: 18, color: accent),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: MetaTheme.inkPrimary,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  subtitle,
                  style: const TextStyle(
                    fontSize: 11,
                    color: MetaTheme.inkSecondary,
                  ),
                  overflow: TextOverflow.ellipsis,
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
    final theme = Theme.of(context);
    final trace = widget.trace;

    final statusChip = widget.running
        ? const StatusChip('Running', StatusKind.info)
        : trace == null
        ? const StatusChip('Standby', StatusKind.neutral)
        : StatusChip(
            trace.status == 'COMPLETED' ? 'Completed' : trace.status,
            trace.status == 'COMPLETED' ? StatusKind.pass : StatusKind.warn,
          );

    return SectionCard(
      title: 'Run control',
      icon: Icons.rocket_launch,
      trailing: statusChip,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Target driver & workflow configuration row
          Row(
            children: [
              if (widget.driver == 'adb')
                Expanded(
                  flex: 3,
                  child: _targetCard(
                    icon: Icons.phone_android,
                    title: 'Android over ADB',
                    subtitle: widget.adbAvailable
                        ? 'Device detected'
                        : 'No device detected',
                    accent: widget.adbAvailable
                        ? MetaTheme.emeraldVerified
                        : MetaTheme.amberWarning,
                  ),
                )
              else if (widget.driver == 'desktop')
                Expanded(
                  flex: 3,
                  child: _targetCard(
                    icon: Icons.desktop_mac,
                    title: 'Desktop OS',
                    subtitle: 'Live input dispatch',
                    accent: MetaTheme.metaBlueDark,
                  ),
                )
              else
                Expanded(
                  flex: 3,
                  child: DropdownButtonFormField<String>(
                    key: ValueKey(widget.selectedWorkflow),
                    initialValue: widget.selectedWorkflow,
                    decoration: const InputDecoration(
                      labelText: 'Workflow',
                      isDense: true,
                    ),
                    items:
                        (widget.workflows.isEmpty
                                ? const [
                                    WorkflowInfo(
                                      workflowId: 'w1',
                                      title: 'W1: Precision canvas grounding',
                                      description: '',
                                    ),
                                    WorkflowInfo(
                                      workflowId: 'w2',
                                      title:
                                          'W2: Voice incident and self-healing',
                                      description: '',
                                    ),
                                  ]
                                : widget.workflows)
                            .map(
                              (w) => DropdownMenuItem(
                                value: w.workflowId,
                                child: Text(
                                  w.title,
                                  style: const TextStyle(fontSize: 13),
                                ),
                              ),
                            )
                            .toList(),
                    onChanged: widget.running
                        ? null
                        : (v) => widget.onSelectWorkflow(v ?? 'w1'),
                  ),
                ),
              const SizedBox(width: 8),
              Expanded(
                flex: 2,
                child: DropdownButtonFormField<String>(
                  key: ValueKey(widget.driver),
                  initialValue: widget.driver,
                  decoration: const InputDecoration(
                    labelText: 'Target device',
                    isDense: true,
                  ),
                  items: const [
                    DropdownMenuItem(
                      value: 'simulated',
                      child: Text('Simulated', style: TextStyle(fontSize: 13)),
                    ),
                    DropdownMenuItem(
                      value: 'desktop',
                      child: Text('Desktop', style: TextStyle(fontSize: 13)),
                    ),
                    DropdownMenuItem(
                      value: 'adb',
                      child: Text(
                        'Android (ADB)',
                        style: TextStyle(fontSize: 13),
                      ),
                    ),
                  ],
                  onChanged: widget.running
                      ? null
                      : (v) => widget.onSelectDriver(v ?? 'simulated'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),

          // Editable intent box
          Container(
            decoration: BoxDecoration(
              color: MetaTheme.surfaceCardElevated,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: MetaTheme.surfaceCardBorder),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(12, 10, 8, 4),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.chat_bubble_outline,
                        size: 16,
                        color: MetaTheme.metaBlueDark,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        'Agent instruction (editable)',
                        style: theme.textTheme.labelLarge,
                      ),
                      const Spacer(),
                      if (widget.intentController.text.isNotEmpty &&
                          !widget.running)
                        IconButton(
                          tooltip: 'Clear input',
                          icon: const Icon(Icons.clear, size: 16),
                          padding: EdgeInsets.zero,
                          constraints: const BoxConstraints(),
                          onPressed: () {
                            widget.intentController.clear();
                            setState(() {});
                          },
                        ),
                    ],
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  child: TextField(
                    controller: widget.intentController,
                    enabled: !widget.running,
                    maxLines: 2,
                    minLines: 1,
                    style: const TextStyle(
                      fontSize: 13,
                      color: MetaTheme.inkPrimary,
                    ),
                    decoration: const InputDecoration(
                      hintText: 'Type an instruction for the agent…',
                      filled: false,
                      border: InputBorder.none,
                      enabledBorder: InputBorder.none,
                      focusedBorder: InputBorder.none,
                      contentPadding: EdgeInsets.symmetric(vertical: 4),
                    ),
                    onSubmitted: (_) => widget.onRun(),
                  ),
                ),
                const Divider(height: 1, color: MetaTheme.surfaceCardBorder),
                Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 4,
                  ),
                  child: Row(
                    children: [
                      _voiceButton(),
                      const Spacer(),
                      TextButton.icon(
                        icon: const Icon(Icons.send, size: 14),
                        label: const Text(
                          'Run',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        style: TextButton.styleFrom(
                          foregroundColor: MetaTheme.metaBlueDark,
                          padding: const EdgeInsets.symmetric(
                            horizontal: 10,
                            vertical: 6,
                          ),
                        ),
                        onPressed: widget.running ? null : widget.onRun,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),

          // Quick suggestion pills
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                const Text(
                  'Suggestions: ',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: MetaTheme.inkMuted,
                  ),
                ),
                ..._quickPrompts.map((prompt) {
                  return Padding(
                    padding: const EdgeInsets.only(right: 6),
                    child: ActionChip(
                      label: Text(prompt, style: const TextStyle(fontSize: 11)),
                      backgroundColor: MetaTheme.surfaceCardElevated,
                      side: const BorderSide(
                        color: MetaTheme.surfaceCardBorder,
                      ),
                      padding: const EdgeInsets.symmetric(horizontal: 4),
                      onPressed: () => _applyQuickPrompt(prompt),
                    ),
                  );
                }),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // Primary run button
          SizedBox(
            width: double.infinity,
            height: 44,
            child: ElevatedButton(
              onPressed: widget.running ? null : widget.onRun,
              style: ElevatedButton.styleFrom(
                backgroundColor: MetaTheme.metaBlue,
                foregroundColor: Colors.white,
                elevation: 0,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
              child: widget.running
                  ? const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.2,
                            color: Colors.white,
                          ),
                        ),
                        SizedBox(width: 12),
                        Text(
                          'Running workflow…',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    )
                  : const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.bolt, size: 18),
                        SizedBox(width: 8),
                        Text(
                          'Run workflow',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ),
            ),
          ),
          const SizedBox(height: 14),

          // Live telemetry stream
          Row(
            children: [
              const Icon(Icons.stream, size: 14, color: MetaTheme.metaBlueDark),
              const SizedBox(width: 6),
              Text('Live trace stream', style: theme.textTheme.labelLarge),
              const Spacer(),
              if (widget.running)
                Container(
                  width: 8,
                  height: 8,
                  decoration: const BoxDecoration(
                    color: MetaTheme.emeraldVerified,
                    shape: BoxShape.circle,
                  ),
                ),
            ],
          ),
          const SizedBox(height: 6),
          Container(
            height: 135,
            decoration: BoxDecoration(
              color: MetaTheme.obsidianBg,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: MetaTheme.surfaceCardBorder),
            ),
            child: widget.spans.isEmpty
                ? Center(
                    child: Text(
                      'Run a workflow to stream spans here.',
                      style: theme.textTheme.bodySmall,
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 6,
                    ),
                    itemCount: widget.spans.length,
                    itemBuilder: (context, index) {
                      final span = widget.spans[index];
                      final name = span['name'] as String? ?? 'span';
                      final lat = (span['latency_ms'] as num?)?.toDouble();
                      return Padding(
                        padding: const EdgeInsets.symmetric(vertical: 2.5),
                        child: Row(
                          children: [
                            const Icon(
                              Icons.check_circle_outline,
                              size: 13,
                              color: MetaTheme.emeraldVerified,
                            ),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                name,
                                style: const TextStyle(
                                  fontSize: 11,
                                  color: MetaTheme.inkPrimary,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            if (lat != null)
                              Text(
                                '${lat.toStringAsFixed(1)}ms',
                                style: const TextStyle(
                                  fontSize: 10,
                                  color: MetaTheme.metaBlueDark,
                                ),
                              ),
                          ],
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}
