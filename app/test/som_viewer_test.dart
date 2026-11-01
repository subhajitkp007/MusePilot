// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:musepilot_hud/core/api_client.dart';
import 'package:musepilot_hud/features/dashboard/som_viewer.dart';

void main() {
  testWidgets('SomViewer renders streamlined 2-toggle options and switches', (
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

    // Verify exactly 2 streamlined tabs are displayed (SAM Grounding & Live Mirror)
    expect(find.text('SAM Grounding'), findsOneWidget);
    expect(find.text('Live Mirror'), findsOneWidget);
    expect(find.text('Raw frame'), findsNothing);

    // Initial state is SAM Grounding (no refresh button)
    expect(find.byIcon(Icons.refresh), findsNothing);

    // Tap Live Mirror -> refresh icon becomes visible for live adb target
    await tester.tap(find.text('Live Mirror'));
    await tester.pumpAndSettle();

    expect(find.byIcon(Icons.refresh), findsOneWidget);
    expect(find.textContaining('Live mirror · ADB'), findsOneWidget);
  });
}
