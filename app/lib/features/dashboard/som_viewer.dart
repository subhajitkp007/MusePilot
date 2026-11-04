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
import 'live_browser_view.dart';

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
  int _liveTimestamp = DateTime.now().millisecondsSinceEpoch;
  Timer? _liveStreamTimer;
  bool _liveStreaming = true;
  bool _hasLoadedLiveFrame = false;
  bool _showLiveBrowser = false;

  @override
  void didUpdateWidget(SomViewer oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.driver != widget.driver) {
      _hasLoadedLiveFrame = false;
      _liveTimestamp = DateTime.now().millisecondsSinceEpoch;
    }
    if (oldWidget.workflow != widget.workflow) {
      _showLiveBrowser = false;
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
    final isShowingLiveMirror = isLiveDriver;
    _syncLiveStream(isShowingLiveMirror);

    final groundingUrl = widget.api.somFrameUrl(
      workflow: widget.workflow,
      state: widget.selectedState,
      traceId: widget.traceId,
    );

    final liveUrl =
        '${widget.api.liveFrameUrl(driver: widget.driver)}&k=$_liveTimestamp';

    final activeDisplayUrl = isShowingLiveMirror ? liveUrl : groundingUrl;

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
            const SizedBox(width: 4),
          ],
          if (widget.workflow == 'w1' && !isLiveDriver) ...[
            InkWell(
              borderRadius: BorderRadius.circular(6),
              onTap: () => openExternalUrl('https://www.tradingview.com/chart/'),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
                decoration: BoxDecoration(
                  color: MetaTheme.surfaceCardElevated,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: MetaTheme.surfaceCardBorder),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.open_in_new,
                      size: 11,
                      color: MetaTheme.metaBlueDark,
                    ),
                    SizedBox(width: 4),
                    Text(
                      'TradingView.com',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                        color: MetaTheme.metaBlueDark,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 6),
          ],
          // Single unified tab indicating active mode: Live Mirror for ADB/Desktop, SAM Grounding or Live Browser for simulated canvas
          InkWell(
            borderRadius: BorderRadius.circular(6),
            onTap: (widget.workflow == 'w1' && !isLiveDriver)
                ? () {
                    setState(() {
                      _showLiveBrowser = !_showLiveBrowser;
                    });
                  }
                : null,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                color: _showLiveBrowser ? MetaTheme.emeraldVerified : MetaTheme.metaBlue,
                borderRadius: BorderRadius.circular(6),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    isShowingLiveMirror
                        ? Icons.phone_android_rounded
                        : (_showLiveBrowser ? Icons.public : Icons.radar),
                    size: 13,
                    color: Colors.white,
                  ),
                  const SizedBox(width: 5),
                  Text(
                    isShowingLiveMirror
                        ? 'Live Mirror'
                        : (_showLiveBrowser ? 'Live Browser View' : 'SAM Grounding'),
                    style: const TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: Colors.white,
                    ),
                  ),
                  if (widget.workflow == 'w1' && !isLiveDriver) ...[
                    const SizedBox(width: 5),
                    Icon(
                      _showLiveBrowser ? Icons.swap_horiz : Icons.touch_app,
                      size: 11,
                      color: Colors.white.withValues(alpha: 0.8),
                    ),
                  ],
                ],
              ),
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

          if (_showLiveBrowser && widget.workflow == 'w1' && !isLiveDriver)
            Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: MetaTheme.metaBlue.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: MetaTheme.metaBlueDark.withValues(alpha: 0.4),
                ),
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.public,
                    size: 16,
                    color: MetaTheme.metaBlueDark,
                  ),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: Text(
                      'LIVE BROWSER ACTIVE (TradingView HTML5 Canvas): Notice 0 DOM elements exist inside the chart. '
                      'Playwright locator clicks fail here. Click the badge above to toggle Meta SAM 3.1 visual grounding.',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: Colors.white,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  InkWell(
                    onTap: () {
                      setState(() {
                        _showLiveBrowser = false;
                      });
                    },
                    borderRadius: BorderRadius.circular(4),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: MetaTheme.metaBlueDark,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: const Text(
                        'View SAM Grounding',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),

          // Grounding canvas display - Matched in height to Run control
          Container(
            height: (isObstructed || isHealed || (_showLiveBrowser && widget.workflow == 'w1' && !isLiveDriver))
                ? 350
                : ((widget.states.length > 1 && !isShowingLiveMirror) ? 398 : 442),
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
                        : (_showLiveBrowser && widget.workflow == 'w1'
                            ? const LiveBrowserWidget(
                                url:
                                    'https://s.tradingview.com/widgetembed/?symbol=BINANCE%3ABTCUSDT&interval=60&theme=dark&style=1&timezone=Etc%2FUTC&locale=en',
                                title: 'TradingView BTC/USD Real-Time Perpetual Market',
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
                              )),
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
                          ] else if (_showLiveBrowser && widget.workflow == 'w1') ...[
                            const Icon(
                              Icons.public,
                              size: 12,
                              color: MetaTheme.emeraldVerified,
                            ),
                            const SizedBox(width: 5),
                            const Text(
                              'Live Browser · Real-Time WebGL/HTML5 Canvas · TradingView BTC/USD',
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.w600,
                                color: Colors.white,
                              ),
                            ),
                          ] else ...[
                            const Icon(
                              Icons.blur_on,
                              size: 12,
                              color: MetaTheme.emeraldVerified,
                            ),
                            const SizedBox(width: 5),
                            const Text(
                              'Grounding · SAM 3.1 + PPT Laser Reticle',
                              style: TextStyle(
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
                  if (!isShowingLiveMirror && !_showLiveBrowser)
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

          // Stage Timeline Scrubber
          if (widget.states.length > 1 && !isShowingLiveMirror && !_showLiveBrowser) ...[
            const SizedBox(height: 10),
            _buildTimelineScrubber(),
          ],
          if (_showLiveBrowser && widget.workflow == 'w1' && !isLiveDriver) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: MetaTheme.surfaceCardElevated,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: MetaTheme.surfaceCardBorder),
              ),
              child: Row(
                children: [
                  const Icon(Icons.show_chart, size: 14, color: MetaTheme.emeraldVerified),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: Text(
                      'INTERACTIVE LIVE CANVAS: Real-time Binance BTC/USDT Perpetual Market • Pan, zoom, and test clicks',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                        color: Colors.white,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  InkWell(
                    onTap: () => openExternalUrl('https://www.tradingview.com/chart/'),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'Open Full Screen',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                            color: MetaTheme.metaBlueDark,
                          ),
                        ),
                        SizedBox(width: 4),
                        Icon(Icons.open_in_new, size: 11, color: MetaTheme.metaBlueDark),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildTimelineScrubber() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: MetaTheme.surfaceCardElevated,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: MetaTheme.surfaceCardBorder),
      ),
      child: Row(
        children: [
          const Icon(
            Icons.timeline_rounded,
            size: 14,
            color: MetaTheme.inkSecondary,
          ),
          const SizedBox(width: 6),
          const Text(
            'STAGE:',
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
              color: MetaTheme.inkSecondary,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  for (final state in widget.states) ...[
                    _buildTimelineChip(state),
                    const SizedBox(width: 6),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTimelineChip(String state) {
    final isSelected = widget.selectedState == state;
    final isObstruction = state.contains('modal_blocked');
    final isRecovery = state.contains('recovered');
    final isFinal = state.contains('final');

    String label;
    IconData icon;
    Color activeColor;

    if (state == 'initial') {
      label = 'T0 · Initial';
      icon = Icons.play_circle_outline;
      activeColor = MetaTheme.metaBlue;
    } else if (isObstruction) {
      label = 'T2 · ⚠️ Blocker';
      icon = Icons.report_problem;
      activeColor = MetaTheme.coralAlert;
    } else if (isRecovery) {
      label = 'T2 · ✓ Healed';
      icon = Icons.auto_fix_high;
      activeColor = MetaTheme.emeraldVerified;
    } else if (isFinal) {
      final stepMatch = RegExp(r'step_(\d+)').firstMatch(state);
      final stepNum = stepMatch != null ? stepMatch.group(1) : '4';
      label = 'T$stepNum · ✦ Verified';
      icon = Icons.verified;
      activeColor = MetaTheme.emeraldVerified;
    } else {
      final stepMatch = RegExp(r'step_(\d+)').firstMatch(state);
      final stepNum = stepMatch != null ? stepMatch.group(1) : '1';
      label = 'T$stepNum · Step $stepNum';
      icon = Icons.adjust;
      activeColor = MetaTheme.metaBlue;
    }

    final chipColor = isSelected ? activeColor : MetaTheme.inkSecondary;

    return Semantics(
      button: true,
      label: label,
      child: InkWell(
        onTap: () => widget.onSelectState(state),
        borderRadius: BorderRadius.circular(6),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: isSelected
                ? activeColor.withValues(alpha: 0.18)
                : MetaTheme.surfaceCard,
            borderRadius: BorderRadius.circular(6),
            border: Border.all(
              color: isSelected ? activeColor : MetaTheme.surfaceCardBorder,
              width: isSelected ? 1.5 : 1.0,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 12, color: chipColor),
              const SizedBox(width: 4),
              Text(
                label,
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                  color: isSelected ? Colors.white : MetaTheme.inkSecondary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
