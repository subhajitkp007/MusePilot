// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Interactive Industry Solution Showcase Switcher for the MusePilot HUD.
library;

import 'package:flutter/material.dart';

import '../../theme/meta_theme.dart';

/// Solution scenario defining business domain and pre-configured execution intent.
class SolutionScenario {
  const SolutionScenario({
    required this.id,
    required this.name,
    required this.industry,
    required this.icon,
    required this.workflowId,
    required this.defaultIntent,
    required this.injectModal,
    required this.businessRoi,
    required this.highlightBadge,
    required this.badgeColor,
  });

  final String id;
  final String name;
  final String industry;
  final IconData icon;
  final String workflowId;
  final String defaultIntent;
  final bool injectModal;
  final String businessRoi;
  final String highlightBadge;
  final Color badgeColor;
}

const List<SolutionScenario> kSolutionScenarios = [
  SolutionScenario(
    id: 'mobile_adb',
    name: 'Android mobile agent',
    industry: 'Samsung Galaxy S24 Ultra',
    icon: Icons.phone_android,
    workflowId: 'w2',
    defaultIntent: 'Stop all alarms and then open Instagram and play reels.',
    injectModal: false,
    businessRoi: 'Zero on-device agent needed; 1:1 hardware control over wireless ADB.',
    highlightBadge: 'Live ADB Touch',
    badgeColor: MetaTheme.emeraldVerified,
  ),
  SolutionScenario(
    id: 'canvas_cad',
    name: 'Northbeam Canvas & CAD',
    industry: 'Northbeam Studio / WebGL',
    icon: Icons.palette,
    workflowId: 'w1',
    defaultIntent:
        'In the Northbeam WebGL workbench, calibrate carrier frequency to 75%, enable adaptive damping loop, lock DSP gain to 0.942, and verify spectral convergence.',
    injectModal: false,
    businessRoi: 'Drives opaque canvas apps where DOM selectors cannot reach.',
    highlightBadge: 'Canvas Grounding',
    badgeColor: MetaTheme.metaBlueDark,
  ),
  SolutionScenario(
    id: 'secops_self_healing',
    name: 'Incident triage and self-healing',
    industry: 'CloudOps SRE War Room',
    icon: Icons.security,
    workflowId: 'w2',
    defaultIntent:
        'Triage the GPU latency spike incident in CloudOps console, resolve the blocking SSO session modal via autonomous replan, and dispatch the Sev-1 alert.',
    injectModal: true,
    businessRoi:
        'Detects modal obstructions, invalidates perception cache, and autonomously replans.',
    highlightBadge: 'Self-Healing Replan',
    badgeColor: MetaTheme.coralAlert,
  ),
  SolutionScenario(
    id: 'enterprise_rpa',
    name: 'Enterprise VDI & Legacy ERP',
    industry: 'SAP / Citrix / Mainframe',
    icon: Icons.corporate_fare,
    workflowId: 'w1',
    defaultIntent:
        'Connect to the financial workstation, calibrate carrier frequency to 75%, lock the adaptive damping loop, set DSP coefficient, and verify batch audit.',
    injectModal: false,
    businessRoi: 'Automates legacy UIs that expose no API, using vision only.',
    highlightBadge: 'Vision RPA',
    badgeColor: MetaTheme.metaBlueDark,
  ),
  SolutionScenario(
    id: 'voice_assistive',
    name: 'Hands-free voice access',
    industry: 'Medical / Assistive / Warehouse',
    icon: Icons.record_voice_over,
    workflowId: 'w2',
    defaultIntent:
        'Extract system anomaly metrics from the CloudOps console, log root cause, and dispatch the Sev-1 incident alert.',
    injectModal: false,
    businessRoi:
        'Hands-free multi-app control powered by Meta Muse Voice Transcribe.',
    highlightBadge: 'Voice Intake',
    badgeColor: MetaTheme.metaBlueDark,
  ),
];

/// Horizontal selector for switching industry solution personas.
class SolutionShowcaseBar extends StatelessWidget {
  const SolutionShowcaseBar({
    required this.selectedScenarioId,
    required this.onSelectScenario,
    required this.running,
    super.key,
  });

  final String selectedScenarioId;
  final ValueChanged<SolutionScenario> onSelectScenario;
  final bool running;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            children: [
              const Icon(
                Icons.explore,
                size: 16,
                color: MetaTheme.metaBlueDark,
              ),
              const SizedBox(width: 8),
              const Text(
                'Solution scenarios',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: MetaTheme.inkPrimary,
                ),
              ),
              const Spacer(),
              Text(
                'Select a scenario to prefill the workflow, target, and intent',
                style: TextStyle(
                  fontSize: 11,
                  color: MetaTheme.inkMuted,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ],
          ),
        ),
        LayoutBuilder(
          builder: (context, constraints) {
            // When screen is wide enough (>= 980px), spread cards across full width with zero gap
            final isWide = constraints.maxWidth >= 980;

            if (isWide) {
              return Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: SizedBox(
                  height: 82,
                  child: Row(
                    children: [
                      for (int i = 0; i < kSolutionScenarios.length; i++) ...[
                        if (i > 0) const SizedBox(width: 10),
                        Expanded(
                          child: _buildCard(kSolutionScenarios[i]),
                        ),
                      ],
                    ],
                  ),
                ),
              );
            }

            // On narrower screens, allow horizontal scrolling
            return SizedBox(
              height: 82,
              child: ListView.separated(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                scrollDirection: Axis.horizontal,
                itemCount: kSolutionScenarios.length,
                separatorBuilder: (context, index) => const SizedBox(width: 10),
                itemBuilder: (context, index) =>
                    _buildCard(kSolutionScenarios[index], width: 220),
              ),
            );
          },
        ),
      ],
    );
  }

  Widget _buildCard(SolutionScenario scenario, {double? width}) {
    final isSelected = scenario.id == selectedScenarioId;

    return InkWell(
      onTap: running ? null : () => onSelectScenario(scenario),
      borderRadius: BorderRadius.circular(10),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        width: width,
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: isSelected
              ? MetaTheme.surfaceCardElevated
              : MetaTheme.surfaceCard,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: isSelected
                ? scenario.badgeColor
                : MetaTheme.surfaceCardBorder,
            width: isSelected ? 1.5 : 1.0,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              children: [
                Icon(
                  scenario.icon,
                  size: 18,
                  color: isSelected
                      ? scenario.badgeColor
                      : MetaTheme.inkSecondary,
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    scenario.name,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: isSelected
                          ? FontWeight.w700
                          : FontWeight.w600,
                      color: isSelected
                          ? MetaTheme.inkPrimary
                          : MetaTheme.inkSecondary,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 6,
                    vertical: 2,
                  ),
                  decoration: BoxDecoration(
                    color: scenario.badgeColor.withValues(
                      alpha: 0.15,
                    ),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    scenario.highlightBadge,
                    style: TextStyle(
                      fontSize: 9,
                      fontWeight: FontWeight.w700,
                      color: scenario.badgeColor,
                    ),
                  ),
                ),
                const Spacer(),
                Text(
                  scenario.industry,
                  style: const TextStyle(
                    fontSize: 10,
                    color: MetaTheme.inkMuted,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
