// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Voice input flow tests: record, transcribe, fallbacks, and auto-stop.
library;

import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:musepilot_hud/core/api_client.dart';
import 'package:musepilot_hud/core/voice_recorder_api.dart';
import 'package:musepilot_hud/features/dashboard/run_panel.dart';
import 'package:musepilot_hud/models/server.dart';

class _FakeRecorder implements VoiceRecorder {
  _FakeRecorder({this.supported = true, this.allowed = true, Uint8List? clip})
    : clip = clip ?? Uint8List.fromList([1, 2, 3, 4]);

  final bool supported;
  final bool allowed;
  final Uint8List clip;
  bool started = false;
  bool stopped = false;

  @override
  bool get isSupported => supported;

  @override
  Future<bool> hasPermission() async => allowed;

  @override
  Future<void> start() async {
    started = true;
  }

  @override
  Future<Uint8List?> stop() async {
    stopped = true;
    return clip;
  }

  @override
  Future<void> dispose() async {}
}

MusePilotApi _mockApi({required void Function() onTranscribe}) {
  return MusePilotApi(
    baseUrl: 'http://test',
    client: MockClient((request) async {
      expect(request.url.path, '/api/voice/transcribe');
      onTranscribe();
      return http.Response(
        jsonEncode({
          'model_id': 'meta-models/muse-voice-transcribe-1.0',
          'transcript': 'Set an alarm for nine AM',
          'confidence': 0.97,
        }),
        200,
      );
    }),
  );
}

Widget _panel({
  required TextEditingController intentController,
  required MusePilotApi api,
  required VoiceRecorder recorder,
}) {
  return MaterialApp(
    home: Scaffold(
      body: SingleChildScrollView(
        child: RunPanel(
          workflows: const [
            WorkflowInfo(workflowId: 'w1', title: 'W1', description: ''),
            WorkflowInfo(workflowId: 'w2', title: 'W2', description: ''),
          ],
          selectedWorkflow: 'w2',
          onSelectWorkflow: (_) {},
          injectModal: false,
          onInjectModal: (_) {},
          driver: 'simulated',
          onSelectDriver: (_) {},
          intentController: intentController,
          running: false,
          onRun: () {},
          spans: const [],
          trace: null,
          baseUrl: 'http://test',
          adbAvailable: false,
          api: api,
          voiceRecorder: recorder,
        ),
      ),
    ),
  );
}

void main() {
  testWidgets('record, stop, and fill intent with transcript', (tester) async {
    final intentController = TextEditingController();
    final recorder = _FakeRecorder();
    var transcribed = false;
    final api = _mockApi(
      onTranscribe: () {
        transcribed = true;
      },
    );
    addTearDown(intentController.dispose);
    addTearDown(api.close);

    await tester.pumpWidget(
      _panel(intentController: intentController, api: api, recorder: recorder),
    );

    await tester.tap(find.text('Voice input'));
    await tester.pump();
    expect(recorder.started, isTrue);
    expect(find.text('Stop · 0:00'), findsOneWidget);

    // Timer ticks across frames while recording.
    await tester.pump(const Duration(seconds: 2));
    expect(find.text('Stop · 0:02'), findsOneWidget);

    await tester.tap(find.text('Stop · 0:02'));
    await tester.pumpAndSettle();
    expect(recorder.stopped, isTrue);
    expect(transcribed, isTrue);
    expect(intentController.text, 'Set an alarm for nine AM');
    expect(find.text('Transcript ready (97% confidence).'), findsOneWidget);
    expect(find.text('Voice input'), findsOneWidget);
  });

  testWidgets('permission denial falls back to manual guidance', (
    tester,
  ) async {
    final intentController = TextEditingController();
    final recorder = _FakeRecorder(allowed: false);
    var transcribed = false;
    final api = _mockApi(
      onTranscribe: () {
        transcribed = true;
      },
    );
    addTearDown(intentController.dispose);
    addTearDown(api.close);

    await tester.pumpWidget(
      _panel(intentController: intentController, api: api, recorder: recorder),
    );

    await tester.tap(find.text('Voice input'));
    await tester.pumpAndSettle();
    expect(recorder.started, isFalse);
    expect(transcribed, isFalse);
    expect(find.text('Voice input unavailable'), findsOneWidget);
    expect(find.textContaining('curl -X POST'), findsOneWidget);
  });

  testWidgets('unsupported platform falls back to manual guidance', (
    tester,
  ) async {
    final intentController = TextEditingController();
    final recorder = _FakeRecorder(supported: false);
    var transcribed = false;
    final api = _mockApi(
      onTranscribe: () {
        transcribed = true;
      },
    );
    addTearDown(intentController.dispose);
    addTearDown(api.close);

    await tester.pumpWidget(
      _panel(intentController: intentController, api: api, recorder: recorder),
    );

    await tester.tap(find.text('Voice input'));
    await tester.pumpAndSettle();
    expect(recorder.started, isFalse);
    expect(transcribed, isFalse);
    expect(find.text('Voice input unavailable'), findsOneWidget);
  });

  testWidgets('recording auto-stops at sixty seconds', (tester) async {
    final intentController = TextEditingController();
    final recorder = _FakeRecorder();
    var transcribed = false;
    final api = _mockApi(
      onTranscribe: () {
        transcribed = true;
      },
    );
    addTearDown(intentController.dispose);
    addTearDown(api.close);

    await tester.pumpWidget(
      _panel(intentController: intentController, api: api, recorder: recorder),
    );

    await tester.tap(find.text('Voice input'));
    await tester.pump();
    expect(find.textContaining('Stop ·'), findsOneWidget);

    await tester.pump(const Duration(seconds: 60));
    await tester.pumpAndSettle();
    expect(recorder.stopped, isTrue);
    expect(transcribed, isTrue);
    expect(intentController.text, 'Set an alarm for nine AM');
  });
}
