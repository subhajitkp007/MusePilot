// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Widget smoke tests for HUD primitives and endpoint configuration.
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:musepilot_hud/core/api_config.dart';
import 'package:musepilot_hud/widgets/metric_card.dart';
import 'package:musepilot_hud/widgets/status_chip.dart';

void main() {
  test('derives WebSocket URLs from HTTP and HTTPS bases', () {
    expect(
      ApiConfig.wsRunsUrl('http://localhost:8501'),
      'ws://localhost:8501/ws/runs',
    );
    expect(
      ApiConfig.wsRunsUrl('https://hud.example.com'),
      'wss://hud.example.com/ws/runs',
    );
  });

  testWidgets('MetricCard renders label, value, and caption', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: MetricCard(
            label: 'Mask hit rate',
            value: '100.0%',
            caption: '0px drift target',
            icon: Icons.gps_fixed,
            tone: MetricTone.good,
          ),
        ),
      ),
    );

    expect(find.text('Mask hit rate'), findsOneWidget);
    expect(find.text('100.0%'), findsOneWidget);
    expect(find.text('0px drift target'), findsOneWidget);
  });

  testWidgets('StatusChip renders pass and fail pills', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: Column(
            children: [StatusChip.pass('PASS'), StatusChip.fail('FAIL')],
          ),
        ),
      ),
    );

    expect(find.text('PASS'), findsOneWidget);
    expect(find.text('FAIL'), findsOneWidget);
  });
}
