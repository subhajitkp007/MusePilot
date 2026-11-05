// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Executive-grade interactive DAG node graph visualizing planned and executing mission steps.
library;

import 'package:flutter/material.dart';

import '../../models/trace.dart';
import '../../theme/meta_theme.dart';
import '../../widgets/section_card.dart';

/// Step plan visualizer: nodes light up as records verify them.
class StepGraphView extends StatefulWidget {
  const StepGraphView({
    super.key,
    required this.steps,
    this.records = const [],
    this.planSummary,
    this.isRunning = false,
    this.selectedStepId,
    this.onSelectStep,
  });

  final List<StepNode> steps;
  final List<StepExecutionRecord> records;
  final String? planSummary;
  final bool isRunning;
  final int? selectedStepId;
  final ValueChanged<int>? onSelectStep;

  @override
  State<StepGraphView> createState() => _StepGraphViewState();
}

class _StepGraphViewState extends State<StepGraphView>
    with SingleTickerProviderStateMixin {
  int? _selectedStepId;
  late AnimationController _pulseController;

  int get _activeStepId =>
      widget.selectedStepId ?? _selectedStepId ?? widget.steps.first.stepId;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    )..repeat(reverse: true);
  }

  @override
  void didUpdateWidget(covariant StepGraphView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.isRunning &&
        widget.records.length > oldWidget.records.length &&
        widget.records.isNotEmpty) {
      _selectedStepId = widget.records.last.step.stepId;
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.steps.isEmpty) {
      return const SizedBox.shrink();
    }

    final selectedStep = widget.steps.firstWhere(
      (s) => s.stepId == _activeStepId,
      orElse: () => widget.steps.first,
    );

    final matchingRecord = widget.records
        .cast<StepExecutionRecord?>()
        .firstWhere(
          (r) => r?.step.stepId == selectedStep.stepId,
          orElse: () => null,
        );

    final completedCount = widget.records.where((r) => r.verdict.passed).length;
    final totalCount = widget.steps.length;
    final progress = totalCount > 0
        ? (completedCount / totalCount).clamp(0.0, 1.0)
        : 0.0;

    return SectionCard(
      title: 'Step plan',
      icon: Icons.hub_rounded,
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (widget.isRunning) ...[
            FadeTransition(
              opacity: _pulseController,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: MetaTheme.metaBlue.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: MetaTheme.metaBlueDark, width: 1),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    SizedBox(
                      width: 8,
                      height: 8,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: MetaTheme.metaBlueDark,
                      ),
                    ),
                    SizedBox(width: 6),
                    Text(
                      'Running',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        color: MetaTheme.metaBlueDark,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 8),
          ],
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: MetaTheme.surfaceCard,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: MetaTheme.surfaceCardBorder),
            ),
            child: Text(
              '$completedCount of $totalCount steps verified (${(progress * 100).toInt()}%)',
              style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w700,
                color: MetaTheme.inkSecondary,
              ),
            ),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Thin linear progress bar
          ClipRRect(
            borderRadius: BorderRadius.circular(2),
            child: LinearProgressIndicator(
              value: progress,
              minHeight: 3,
              backgroundColor: MetaTheme.surfaceCardBorder,
              valueColor: const AlwaysStoppedAnimation<Color>(
                MetaTheme.emeraldVerified,
              ),
            ),
          ),
          const SizedBox(height: 14),

          // Interactive DAG horizontal step flow
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            physics: const BouncingScrollPhysics(),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                for (int i = 0; i < widget.steps.length; i++) ...[
                  _buildStepNode(widget.steps[i]),
                  if (i < widget.steps.length - 1)
                    _buildDirectedConnector(sourceStep: widget.steps[i]),
                ],
              ],
            ),
          ),

          const SizedBox(height: 14),

          // Node Inspector Card (tap to inspect step details)
          _buildNodeDetailCard(selectedStep, matchingRecord),
        ],
      ),
    );
  }

  Widget _buildStepNode(StepNode step) {
    final record = widget.records.cast<StepExecutionRecord?>().firstWhere(
      (r) => r?.step.stepId == step.stepId,
      orElse: () => null,
    );

    final isSelected = _activeStepId == step.stepId;
    final isVerified = record != null && record.verdict.passed;
    final isHealed = record != null && record.selfHealed;
    final isFailed = record != null && !record.verdict.passed;

    // Node accent colors
    Color borderColor;
    Color bgColor;
    IconData statusIcon;

    if (isHealed) {
      borderColor = MetaTheme.emeraldVerified;
      bgColor = MetaTheme.emeraldVerified.withValues(alpha: 0.12);
      statusIcon = Icons.auto_fix_high_rounded;
    } else if (isVerified) {
      borderColor = MetaTheme.emeraldVerified;
      bgColor = MetaTheme.emeraldVerified.withValues(alpha: 0.10);
      statusIcon = Icons.check_circle_rounded;
    } else if (isFailed) {
      borderColor = MetaTheme.coralAlert;
      bgColor = MetaTheme.coralAlert.withValues(alpha: 0.15);
      statusIcon = Icons.warning_rounded;
    } else {
      // Pending
      borderColor = isSelected
          ? MetaTheme.metaBlue
          : MetaTheme.surfaceCardBorder;
      bgColor = MetaTheme.surfaceCard;
      statusIcon = Icons.circle_outlined;
    }

    return InkWell(
      onTap: () {
        setState(() => _selectedStepId = step.stepId);
        widget.onSelectStep?.call(step.stepId);
      },
      borderRadius: BorderRadius.circular(10),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 300),
        width: 170,
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: isSelected ? MetaTheme.metaBlue : borderColor,
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 6,
                    vertical: 2,
                  ),
                  decoration: BoxDecoration(
                    color: MetaTheme.obsidianBg,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(
                      color: borderColor.withValues(alpha: 0.5),
                    ),
                  ),
                  child: Text(
                    'Step ${step.stepId}',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      color: isVerified
                          ? MetaTheme.emeraldVerified
                          : MetaTheme.inkSecondary,
                    ),
                  ),
                ),
                const Spacer(),
                Icon(statusIcon, size: 14, color: borderColor),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                _buildOpIcon(step.operation),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    _capitalize(step.operation),
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: MetaTheme.inkPrimary,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
              decoration: BoxDecoration(
                color: MetaTheme.metaBlue.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                'Mask #${step.targetMaskId}',
                style: const TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                  color: MetaTheme.metaBlueDark,
                ),
              ),
            ),
            const SizedBox(height: 6),
            Text(
              step.expectedOutcome,
              style: const TextStyle(
                fontSize: 10,
                color: MetaTheme.inkSecondary,
                height: 1.2,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }

  String _capitalize(String value) =>
      value.isEmpty ? value : '${value[0].toUpperCase()}${value.substring(1)}';

  Widget _buildDirectedConnector({required StepNode sourceStep}) {
    final sourceRecord = widget.records.cast<StepExecutionRecord?>().firstWhere(
      (r) => r?.step.stepId == sourceStep.stepId,
      orElse: () => null,
    );
    final isSourceComplete =
        sourceRecord != null && sourceRecord.verdict.passed;

    Color arrowColor = MetaTheme.surfaceCardBorder;
    if (isSourceComplete) {
      arrowColor = MetaTheme.emeraldVerified;
    }

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4),
      child: SizedBox(
        width: 32,
        child: Row(
          children: [
            Expanded(child: Container(height: 2, color: arrowColor)),
            Icon(Icons.chevron_right_rounded, size: 16, color: arrowColor),
          ],
        ),
      ),
    );
  }

  Widget _buildOpIcon(String operation) {
    IconData icon;
    Color color;
    switch (operation.toLowerCase()) {
      case 'click':
        icon = Icons.touch_app_rounded;
        color = MetaTheme.metaBlue;
      case 'type':
        icon = Icons.keyboard_rounded;
        color = MetaTheme.metaBlueDark;
      case 'drag':
        icon = Icons.swipe_rounded;
        color = MetaTheme.metaBlueDark;
      case 'wait':
        icon = Icons.timer_rounded;
        color = MetaTheme.amberWarning;
      case 'verify':
        icon = Icons.verified_rounded;
        color = MetaTheme.emeraldVerified;
      default:
        icon = Icons.smart_button_rounded;
        color = MetaTheme.inkSecondary;
    }
    return Container(
      padding: const EdgeInsets.all(3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Icon(icon, size: 14, color: color),
    );
  }

  Widget _buildNodeDetailCard(StepNode step, StepExecutionRecord? record) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: MetaTheme.surfaceCard,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: MetaTheme.surfaceCardBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                decoration: BoxDecoration(
                  color: MetaTheme.metaBlue.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  'Step ${step.stepId} · ${_capitalize(step.operation)}',
                  style: const TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    color: MetaTheme.metaBlueDark,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Text(
                'Target: mask #${step.targetMaskId}',
                style: const TextStyle(
                  fontSize: 11,
                  color: MetaTheme.inkSecondary,
                ),
              ),
              if (step.inputValue != null) ...[
                const SizedBox(width: 8),
                Text(
                  'Value: "${step.inputValue}"',
                  style: const TextStyle(
                    fontSize: 11,
                    color: MetaTheme.amberWarning,
                  ),
                ),
              ],
              const Spacer(),
              if (record != null)
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 2,
                  ),
                  decoration: BoxDecoration(
                    color:
                        (record.verdict.passed
                                ? MetaTheme.emeraldVerified
                                : MetaTheme.coralAlert)
                            .withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(
                      color: record.verdict.passed
                          ? MetaTheme.emeraldVerified
                          : MetaTheme.coralAlert,
                      width: 1,
                    ),
                  ),
                  child: Text(
                    record.verdict.passed
                        ? (record.selfHealed
                              ? 'Self-healed · Verified'
                              : 'Verified')
                        : 'Failed',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      color: record.verdict.passed
                          ? MetaTheme.emeraldVerified
                          : MetaTheme.coralAlert,
                    ),
                  ),
                )
              else
                const Text(
                  'Awaiting execution',
                  style: TextStyle(fontSize: 11, color: MetaTheme.inkSecondary),
                ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Planner reasoning: ${step.reasoning.isNotEmpty ? step.reasoning : "Ground the target element and verify the outcome."}',
            style: const TextStyle(
              fontSize: 11,
              color: MetaTheme.inkPrimary,
              height: 1.3,
            ),
          ),
          if (record != null) ...[
            const SizedBox(height: 6),
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Receipt: centroid [${record.receipt.frameCentroidPx.join(", ")}] · ${record.receipt.executionLatencyMs.toStringAsFixed(1)}ms · attempt #${record.attemptNumber}',
                    style: const TextStyle(
                      fontSize: 10,
                      color: MetaTheme.inkSecondary,
                    ),
                  ),
                ),
                Text(
                  'Confidence: ${(record.verdict.confidence * 100).toInt()}% • Observed: ${record.verdict.observedChange}',
                  style: const TextStyle(
                    fontSize: 10,
                    color: MetaTheme.emeraldVerified,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
