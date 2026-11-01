// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:musepilot_hud/core/api_client.dart';
import 'package:musepilot_hud/features/dashboard/som_viewer.dart';

void main() {
  testWidgets('SomViewer automatically displays Live Mirror single tab for adb driver', (
    tester,
  ) async {
    final client = MockClient((request) async {
      return http.Response('fake-image-bytes', 200);
    });
    final api = MusePilotApi(baseUrl: 'http://localhost:8501', client: client);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SomViewer(
            api: api,
            workflow: 'w2',
            states: const ['step_0_initial', 'step_1_final'],
            selectedState: 'step_0_initial',
            onSelectState: (_) {},
            traceId: 'trace-123',
            driver: 'adb',
          ),
        ),
      ),
    );

    // Verify single tab is Live Mirror for ADB
    expect(find.text('Live Mirror'), findsOneWidget);
    expect(find.text('SAM Grounding'), findsNothing);

    // Refresh icon and streaming badge are visible for live adb target
    expect(find.byIcon(Icons.refresh), findsOneWidget);
    expect(find.textContaining('Live mirror · ADB'), findsOneWidget);
  });

  testWidgets('SomViewer automatically displays SAM Grounding single tab for simulated driver', (
    tester,
  ) async {
    final client = MockClient((request) async {
      return http.Response('fake-image-bytes', 200);
    });
    final api = MusePilotApi(baseUrl: 'http://localhost:8501', client: client);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SomViewer(
            api: api,
            workflow: 'w1',
            states: const ['initial', 'step_1', 'step_2_final'],
            selectedState: 'initial',
            onSelectState: (_) {},
            traceId: 'trace-123',
            driver: 'simulated',
          ),
        ),
      ),
    );

    // Verify single tab is SAM Grounding for simulated driver
    expect(find.text('SAM Grounding'), findsOneWidget);
    expect(find.text('Live Mirror'), findsNothing);

    // Refresh icon is not present for simulated driver
    expect(find.byIcon(Icons.refresh), findsNothing);
    expect(find.textContaining('Grounding · SAM 3.1'), findsOneWidget);
  });
}
