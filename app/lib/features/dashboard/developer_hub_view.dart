// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Developer Hub & SDK Integration view with interactive code snippets and cURL commands.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../theme/meta_theme.dart';
import '../../widgets/section_card.dart';

/// Interactive developer integration guide.
class DeveloperHubView extends StatefulWidget {
  const DeveloperHubView({required this.baseUrl, super.key});

  final String baseUrl;

  @override
  State<DeveloperHubView> createState() => _DeveloperHubViewState();
}

class _DeveloperHubViewState extends State<DeveloperHubView> {
  int _selectedTab = 0;

  void _copyToClipboard(String code, String label) {
    Clipboard.setData(ClipboardData(text: code));
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        backgroundColor: MetaTheme.emeraldVerified,
        content: Text('Copied $label to clipboard!'),
        duration: const Duration(seconds: 2),
      ),
    );
  }

  Widget _codeBlock({
    required String code,
    required String language,
    required String label,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: MetaTheme.obsidianBg,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: MetaTheme.surfaceCardBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: const BoxDecoration(
              color: MetaTheme.surfaceCardElevated,
              borderRadius: BorderRadius.vertical(top: Radius.circular(8)),
            ),
            child: Row(
              children: [
                Icon(
                  language == 'python'
                      ? Icons.code
                      : language == 'bash'
                      ? Icons.terminal
                      : Icons.electrical_services,
                  size: 16,
                  color: MetaTheme.metaBlueDark,
                ),
                const SizedBox(width: 8),
                Text(
                  label,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: MetaTheme.inkPrimary,
                  ),
                ),
                const Spacer(),
                TextButton.icon(
                  icon: const Icon(Icons.copy, size: 14),
                  label: const Text('Copy', style: TextStyle(fontSize: 12)),
                  style: TextButton.styleFrom(
                    foregroundColor: MetaTheme.metaBlueDark,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 4,
                    ),
                  ),
                  onPressed: () => _copyToClipboard(code, label),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(14),
            child: SelectableText(
              code,
              style: const TextStyle(
                fontFamilyFallback: ['Menlo', 'Consolas', 'monospace'],
                fontSize: 12,
                color: MetaTheme.inkPrimary,
                height: 1.5,
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final pythonCode =
        '''
from pathlib import Path

from musepilot.sdk import MusePilotClient

with MusePilotClient("${widget.baseUrl}") as mp:
    # Pre-flight health: readiness plus configured model IDs
    health = mp.health()
    print(f"SAM: {health['sam_model_id']} | Planner: {health['planner_model_id']}")

    # Run a workflow and read the deterministic trace
    trace = mp.run(
        workflow_id="w1",
        custom_intent="Set frequency to 75% and commit batch",
        driver="simulated",  # "simulated" | "desktop" | "adb"
    )
    for record in trace["records"]:
        step = record["step"]
        print(f"Step {step['step_id']}: {step['operation']} @ mask #{step['target_mask_id']}")
        print(f"  Verified: {record['verdict']['passed']}")

    # Transcribe a spoken command, then run it as intent
    heard = mp.transcribe(Path("command.wav"))["transcript"]
    mp.run("w2", custom_intent=heard)
''';

    final curlCode =
        '''
# 1. Pre-flight health check
curl -X GET "${widget.baseUrl}/api/health"

# 2. Trigger a run via REST
curl -X POST "${widget.baseUrl}/api/runs" \\
  -H "Content-Type: application/json" \\
  -d '{
    "workflow_id": "w1",
    "driver": "simulated",
    "custom_intent": "Set frequency to 75% and commit batch",
    "inject_modal": false
  }'

# 3. Transcribe a WAV voice command
curl -X POST "${widget.baseUrl}/api/voice/transcribe" \\
  -F "audio=@command.wav" \\
  -F "workflow_id=w2"
''';

    final wsCode =
        '''
// JavaScript / WebSocket client integration
const socket = new WebSocket("${widget.baseUrl.replaceAll('http', 'ws')}/ws/runs");

socket.onopen = () => {
  socket.send(JSON.stringify({
    workflow_id: "w2",
    driver: "simulated",
    custom_intent: "Triage incident alert",
    inject_modal: true
  }));
};

socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === "span") {
    console.log(`[Telemetry] \${data.span.name}: \${data.span.latency_ms}ms`);
  } else if (data.type === "step_record") {
    console.log(`[Step] Verified: \${data.record.verdict.passed}`);
  } else if (data.type === "complete") {
    console.log("Run completed:", data.trace.trace_id);
  }
};
''';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionCard(
          title: 'Developer hub and SDK',
          icon: Icons.integration_instructions,
          trailing: Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: MetaTheme.metaBlue.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(6),
            ),
            child: const Text(
              'Stable API',
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w700,
                color: MetaTheme.metaBlueDark,
              ),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Call MusePilot from CI pipelines, backend services, or mobile apps with the Python SDK, REST, or WebSocket streaming.',
                style: TextStyle(fontSize: 13, color: MetaTheme.inkSecondary),
              ),
              const SizedBox(height: 14),

              // Tab Selector
              Row(
                children: [
                  _tabBtn(0, 'Python SDK', Icons.code),
                  const SizedBox(width: 8),
                  _tabBtn(1, 'cURL and REST', Icons.terminal),
                  const SizedBox(width: 8),
                  _tabBtn(2, 'WebSocket', Icons.electrical_services),
                ],
              ),
              const SizedBox(height: 14),

              // Code Display
              if (_selectedTab == 0)
                _codeBlock(
                  code: pythonCode,
                  language: 'python',
                  label: 'Python SDK quickstart',
                )
              else if (_selectedTab == 1)
                _codeBlock(
                  code: curlCode,
                  language: 'bash',
                  label: 'REST examples',
                )
              else
                _codeBlock(
                  code: wsCode,
                  language: 'javascript',
                  label: 'WebSocket run streaming',
                ),

              const SizedBox(height: 14),
              Row(
                children: [
                  const Icon(
                    Icons.api,
                    size: 16,
                    color: MetaTheme.emeraldVerified,
                  ),
                  const SizedBox(width: 8),
                  const Text(
                    'OpenAPI document: ',
                    style: TextStyle(
                      fontSize: 12,
                      color: MetaTheme.inkSecondary,
                    ),
                  ),
                  Flexible(
                    child: Text(
                      '${widget.baseUrl}/api/openapi.json',
                      style: const TextStyle(
                        fontSize: 12,
                        fontFamilyFallback: ['Menlo', 'Consolas', 'monospace'],
                        fontWeight: FontWeight.w600,
                        color: MetaTheme.metaBlueDark,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _tabBtn(int index, String label, IconData icon) {
    final active = _selectedTab == index;
    return InkWell(
      onTap: () => setState(() => _selectedTab = index),
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
        decoration: BoxDecoration(
          color: active ? MetaTheme.metaBlue : MetaTheme.surfaceCardElevated,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: active ? MetaTheme.metaBlue : MetaTheme.surfaceCardBorder,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 14,
              color: active ? Colors.white : MetaTheme.inkSecondary,
            ),
            const SizedBox(width: 6),
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                fontWeight: active ? FontWeight.w700 : FontWeight.w500,
                color: active ? Colors.white : MetaTheme.inkSecondary,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
