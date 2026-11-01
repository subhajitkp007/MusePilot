// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// SAM 3.1 Set-of-Mark grounding viewer with streamlined layer toggles.
library;

import 'dart:async';

import 'package:flutter/material.dart';

import '../../../core/api_client.dart';
import '../../../models/trace.dart';
import '../../../theme/meta_theme.dart';
import '../../../widgets/section_card.dart';

/// Grounding view layer: SAM 3.1 masks with numbered target badges,
/// or direct device view (live mirror for ADB/desktop, clean screen for simulated).
enum ViewerLayer {
  grounding,
  device,
}

/// Compares canvas frames with SAM 3.1 segmentations and the live device view.
class SomViewer extends StatefulWidget {
  const SomViewer({
    required this.api,
    required this.workflow,
    required this.states,
    required this.selectedState,
    required this.onSelectState,
    required this.traceId,
    this.isRunning = false,
    this.driver = 'simulated',
    this.spans = const [],
    this.liveRecords = const [],
    super.key,
  });

  final MusePilotApi api;
  final String workflow;
  final List<String> states;
  final String selectedState;
  final ValueChanged<String> onSelectState;
  final String? traceId;
  final bool isRunning;
  final String driver;
  final List<Map<String, dynamic>> spans;
  final List<StepExecutionRecord> liveRecords;

  @override
  State<SomViewer> createState() => _SomViewerState();
}

class _SomViewerState extends State<SomViewer> {
  ViewerLayer _activeLayer = ViewerLayer.grounding;
  int _liveTimestamp = DateTime.now().millisecondsSinceEpoch;
  Timer? _liveStreamTimer;
  bool _liveStreaming = true;
  bool _hasLoadedLiveFrame = false;
  bool _autoSwitch = true;

  @override
  void didUpdateWidget(SomViewer oldWidget) {
    super.didUpdateWidget(oldWidget);

    if (!_autoSwitch) return;

    // Run just started
    if (!oldWidget.isRunning && widget.isRunning) {
      if (_activeLayer != ViewerLayer.grounding) {
        setState(() => _activeLayer = ViewerLayer.grounding);
      }
      return;
    }

    // Run just completed
    if (oldWidget.isRunning && !widget.isRunning) {
      if (_activeLayer != ViewerLayer.grounding) {
        setState(() => _activeLayer = ViewerLayer.grounding);
      }
      return;
    }

    // During run: switch dynamically based on active span component across mobile and canvas
    if (widget.isRunning && widget.spans.length != oldWidget.spans.length) {
      if (widget.spans.isNotEmpty) {
        final latest = widget.spans.last;
        final comp =
            (latest['component'] ?? latest['name'] ?? '').toString().toLowerCase();

        if (comp.contains('dispatch') ||
            comp.contains('exec') ||
            comp.contains('device') ||
            comp.contains('mobile') ||
            comp.contains('action')) {
          // Execution/dispatch phase -> Device view (live mirror or clean screen)
          if (_activeLayer != ViewerLayer.device) {
            setState(() => _activeLayer = ViewerLayer.device);
          }
        } else if (comp.contains('sam') ||
            comp.contains('percept') ||
            comp.contains('verif') ||
            comp.contains('ground')) {
          // Perception / Verification phase -> SAM 3.1 masks and badges
          if (_activeLayer != ViewerLayer.grounding) {
            setState(() => _activeLayer = ViewerLayer.grounding);
          }
        }
      }
    }
  }

  @override
  void dispose() {
    _liveStreamTimer?.cancel();
    super.dispose();
  }

  void _syncLiveStream(bool isShowingLiveMirror) {
    if (isShowingLiveMirror && _liveStreaming) {
      if (_liveStreamTimer == null || !_liveStreamTimer!.isActive) {
        _liveStreamTimer = Timer.periodic(const Duration(milliseconds: 250), (_) {
          if (!mounted) return;
          setState(() {
            _liveTimestamp = DateTime.now().millisecondsSinceEpoch;
          });
        });
      }
    } else {
      _liveStreamTimer?.cancel();
      _liveStreamTimer = null;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isObstructed = widget.selectedState.contains('modal_blocked');
    final isHealed = widget.selectedState.contains('modal_dismissed');
    final isLiveDriver = widget.driver == 'adb' || widget.driver == 'desktop';

    // In device mode, load the real live stream if on ADB/Desktop; otherwise load the unsegmented frame.
    final isShowingLiveMirror = _activeLayer == ViewerLayer.device && isLiveDriver;
    _syncLiveStream(isShowingLiveMirror);

    final groundingUrl = widget.api.somFrameUrl(
      workflow: widget.workflow,
      state: widget.selectedState,
      traceId: widget.traceId,
    );

    final rawFrameUrl = widget.api.rawFrameUrl(
      workflow: widget.workflow,
      state: widget.selectedState,
      traceId: widget.traceId,
    );

    final liveUrl =
        '${widget.api.liveFrameUrl(driver: widget.driver)}&k=$_liveTimestamp';

    final activeDisplayUrl = _activeLayer == ViewerLayer.grounding
        ? groundingUrl
        : (isShowingLiveMirror ? liveUrl : rawFrameUrl);

    return SectionCard(
      title: 'Visual grounding',
      icon: Icons.radar,
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (isShowingLiveMirror) ...[
            InkWell(
              borderRadius: BorderRadius.circular(4),
              onTap: () {
                setState(() {
                  _liveStreaming = !_liveStreaming;
                });
              },
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                decoration: BoxDecoration(
                  color: _liveStreaming
                      ? MetaTheme.emeraldVerified.withValues(alpha: 0.15)
                      : MetaTheme.surfaceCardElevated,
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(
                    color: _liveStreaming
                        ? MetaTheme.emeraldVerified.withValues(alpha: 0.5)
                        : MetaTheme.surfaceCardBorder,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: BoxDecoration(
                        color: _liveStreaming
                            ? MetaTheme.emeraldVerified
                            : Colors.grey,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 4),
                    Text(
                      _liveStreaming ? 'STREAMING' : 'PAUSED',
                      style: TextStyle(
                        fontSize: 9,
                        fontWeight: FontWeight.bold,
                        color: _liveStreaming
                            ? MetaTheme.emeraldVerified
                            : Colors.grey,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 4),
            IconButton(
              icon: const Icon(
                Icons.refresh,
                size: 16,
                color: MetaTheme.metaBlueDark,
              ),
              tooltip: 'Refresh live mirror',
              onPressed: () {
                setState(() {
                  _liveTimestamp = DateTime.now().millisecondsSinceEpoch;
                });
              },
            ),
          ],
          Container(
            padding: const EdgeInsets.all(2),
            decoration: BoxDecoration(
              color: MetaTheme.surfaceCardElevated,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: MetaTheme.surfaceCardBorder),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                _layerButton(
                  layer: ViewerLayer.grounding,
                  label: 'SAM Grounding',
                  active: _activeLayer == ViewerLayer.grounding,
                ),
                _layerButton(
                  layer: ViewerLayer.device,
                  label: isLiveDriver ? 'Live Mirror' : 'Device View',
                  active: _activeLayer == ViewerLayer.device,
                ),
                const SizedBox(width: 4),
                InkWell(
                  borderRadius: BorderRadius.circular(6),
                  onTap: () {
                    setState(() {
                      _autoSwitch = !_autoSwitch;
                    });
                  },
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                    decoration: BoxDecoration(
                      color: _autoSwitch
                          ? MetaTheme.metaBlueDark.withValues(alpha: 0.25)
                          : Colors.transparent,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(
                        color: _autoSwitch
                            ? MetaTheme.metaBlueDark.withValues(alpha: 0.6)
                            : Colors.transparent,
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.auto_awesome,
                          size: 11,
                          color: _autoSwitch ? MetaTheme.metaBlueDark : Colors.grey,
                        ),
                        const SizedBox(width: 3),
                        Text(
                          'AUTO',
                          style: TextStyle(
                            fontSize: 9,
                            fontWeight: FontWeight.bold,
                            color: _autoSwitch ? MetaTheme.metaBlueDark : Colors.grey,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Self-healing recovery banner if in modal state
          if (isObstructed)
            Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: MetaTheme.coralAlert.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: MetaTheme.coralAlert.withValues(alpha: 0.4),
                ),
              ),
              child: const Row(
                children: [
                  Icon(
                    Icons.report_problem,
                    size: 16,
                    color: MetaTheme.coralAlert,
                  ),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Modal obstruction: verification triggered self-healing. '
                      'The visual cache was invalidated and the plan replanned.',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: MetaTheme.coralAlert,
                      ),
                    ),
                  ),
                ],
              ),
            ),

          if (isHealed)
            Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: MetaTheme.emeraldVerified.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: MetaTheme.emeraldVerified.withValues(alpha: 0.4),
                ),
              ),
              child: const Row(
                children: [
                  Icon(
                    Icons.auto_fix_high,
                    size: 16,
                    color: MetaTheme.emeraldVerified,
                  ),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Self-healing succeeded: the blocking modal was dismissed '
                      'and execution resumed toward the original goal.',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: MetaTheme.emeraldVerified,
                      ),
                    ),
                  ),
                ],
              ),
            ),

          // Grounding canvas display - Matched in height to Run control
          Container(
            height: isObstructed || isHealed ? 390 : 442,
            width: double.infinity,
            decoration: BoxDecoration(
              color: MetaTheme.obsidianBg,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: widget.isRunning || isObstructed
                    ? MetaTheme.coralAlert
                    : MetaTheme.surfaceCardBorder,
                width: widget.isRunning ? 2.0 : 1.0,
              ),
            ),
            clipBehavior: Clip.antiAlias,
            child: Stack(
                children: [
                  Center(
                    child: isShowingLiveMirror
                        ? Image.network(
                            liveUrl,
                            fit: BoxFit.contain,
                            gaplessPlayback: true,
                            loadingBuilder: (context, child, progress) {
                              if (progress == null) {
                                _hasLoadedLiveFrame = true;
                                return child;
                              }
                              if (_hasLoadedLiveFrame) {
                                return child;
                              }
                              return const Center(
                                child: CircularProgressIndicator(),
                              );
                            },
                            errorBuilder: (context, error, stack) => Center(
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(
                                    Icons.phone_android,
                                    size: 36,
                                    color: theme.disabledColor,
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    'No live frame for the ${widget.driver} target.',
                                    style: const TextStyle(fontSize: 12),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    'Run on a connected target, then refresh.',
                                    style: theme.textTheme.bodySmall,
                                  ),
                                ],
                              ),
                            ),
                          )
                        : Image.network(
                            activeDisplayUrl,
                            fit: BoxFit.contain,
                            gaplessPlayback: true,
                            loadingBuilder: (context, child, progress) {
                              if (progress == null) {
                                _hasLoadedLiveFrame = true;
                                return child;
                              }
                              if (_hasLoadedLiveFrame) {
                                return child;
                              }
                              return const Center(
                                child: CircularProgressIndicator(),
                              );
                            },
                            errorBuilder: (context, error, stack) => Center(
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(
                                    Icons.broken_image_outlined,
                                    size: 36,
                                    color: theme.disabledColor,
                                  ),
                                  const SizedBox(height: 8),
                                  const Text('Frame unavailable for this state.'),
                                ],
                              ),
                            ),
                          ),
                  ),
                  // Overlay telemetry tag
                  Positioned(
                    top: 10,
                    left: 10,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.black.withValues(alpha: 0.85),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          if (isShowingLiveMirror) ...[
                            Icon(
                              widget.driver == 'adb'
                                    ? Icons.phone_android
                                    : Icons.desktop_mac,
                              size: 12,
                              color: MetaTheme.metaBlueDark,
                            ),
                            const SizedBox(width: 5),
                            Text(
                              'Live mirror · ${widget.driver.toUpperCase()} · ${_liveStreaming ? "Live Stream (Fast)" : "Paused"}',
                              style: const TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.w600,
                                color: Colors.white,
                              ),
                            ),
                          ] else ...[
                            Icon(
                              _activeLayer == ViewerLayer.grounding
                                  ? Icons.blur_on
                                  : Icons.screenshot_monitor,
                              size: 12,
                              color: _activeLayer == ViewerLayer.grounding
                                  ? MetaTheme.emeraldVerified
                                  : Colors.white70,
                            ),
                            const SizedBox(width: 5),
                            Text(
                              _activeLayer == ViewerLayer.grounding
                                  ? (widget.driver == 'adb'
                                      ? 'Grounding · SAM 3.1 masks'
                                      : 'Grounding · SAM 3.1 + PPT Laser Reticle')
                                  : (widget.driver == 'adb'
                                      ? 'Device View · Clean screen'
                                      : 'Device View · Laser Grounding'),
                              style: const TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.w600,
                                color: Colors.white,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),

                  // PPT Laser pointer indicator (for non-Android simulation & canvas)
                  if (widget.driver != 'adb')
                    Positioned(
                      top: 10,
                      right: 10,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: const Color(0xFF1E1528).withValues(alpha: 0.9),
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: MetaTheme.coralAlert.withValues(alpha: 0.5)),
                        ),
                        child: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.gps_fixed, size: 11, color: MetaTheme.coralAlert),
                            SizedBox(width: 4),
                            Text(
                              'PPT LASER CENTROID ✦ ACTIVE',
                              style: TextStyle(
                                fontSize: 9,
                                fontWeight: FontWeight.bold,
                                color: MetaTheme.coralAlert,
                                letterSpacing: 0.5,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _layerButton({
    required ViewerLayer layer,
    required String label,
    required bool active,
  }) {
    return Semantics(
      button: true,
      label: label,
      child: InkWell(
        onTap: () => setState(() => _activeLayer = layer),
        borderRadius: BorderRadius.circular(6),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
          decoration: BoxDecoration(
            color: active ? MetaTheme.metaBlue : Colors.transparent,
            borderRadius: BorderRadius.circular(6),
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: 11,
              fontWeight: active ? FontWeight.w700 : FontWeight.w500,
              color: active ? Colors.white : MetaTheme.inkSecondary,
            ),
          ),
        ),
      ),
    );
  }
}
