// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// SAM 3.1 Set-of-Mark grounding viewer with streamlined layer toggles.
library;

import 'package:flutter/material.dart';

import '../../../core/api_client.dart';
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

  @override
  State<SomViewer> createState() => _SomViewerState();
}

class _SomViewerState extends State<SomViewer> {
  ViewerLayer _activeLayer = ViewerLayer.grounding;
  int _liveTimestamp = DateTime.now().millisecondsSinceEpoch;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isObstructed = widget.selectedState.contains('modal_blocked');
    final isHealed = widget.selectedState.contains('modal_dismissed');
    final isLiveDriver = widget.driver == 'adb' || widget.driver == 'desktop';

    // In device mode, load the real live stream if on ADB/Desktop; otherwise load the unsegmented frame.
    final isShowingLiveMirror = _activeLayer == ViewerLayer.device && isLiveDriver;

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
          if (isShowingLiveMirror)
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
                            loadingBuilder: (context, child, progress) =>
                                progress == null
                                ? child
                                : const Center(
                                    child: CircularProgressIndicator(),
                                  ),
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
                            loadingBuilder: (context, child, progress) =>
                                progress == null
                                ? child
                                : const Center(
                                    child: CircularProgressIndicator(),
                                  ),
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
                              'Live mirror · ${widget.driver.toUpperCase()} · tap refresh to update',
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
                                  ? 'Grounding · SAM 3.1 masks'
                                  : 'Device View · Clean screen',
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
    return InkWell(
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
    );
  }
}
