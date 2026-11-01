// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// API client tests against a mock HTTP transport.
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:musepilot_hud/core/api_client.dart';

void main() {
  test('getHealth parses readiness report', () async {
    final client = MusePilotApi(
      baseUrl: 'http://test',
      client: MockClient((request) async {
        expect(request.url.path, '/api/health');
        return http.Response(
          jsonEncode({
            'passed': true,
            'execution_mode': 'simulated',
            'sam_model_id': 'meta-models/sam-3.1',
            'planner_model_id': 'meta-models/muse-spark',
            'verifier_model_id': 'meta-models/muse-spark-open-1026',
            'partner_provider': 'baseten',
            'display_dpi_scale': 2.0,
            'checks': {},
          }),
          200,
        );
      }),
    );

    final health = await client.getHealth();
    expect(health.passed, isTrue);
    expect(health.executionMode, 'simulated');
    client.close();
  });

  test('createRun posts the run request and parses the trace', () async {
    final golden = File('test/fixtures/golden_w1.json').readAsStringSync();
    final client = MusePilotApi(
      baseUrl: 'http://test',
      client: MockClient((request) async {
        expect(request.method, 'POST');
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['workflow_id'], 'w1');
        expect(body['inject_modal'], isFalse);
        return http.Response(golden, 200);
      }),
    );

    final trace = await client.createRun(workflowId: 'w1', injectModal: false);
    expect(trace.workflowId, 'w1');
    expect(trace.records, hasLength(4));
    client.close();
  });

  test('server errors surface the detail message', () async {
    final client = MusePilotApi(
      baseUrl: 'http://test',
      client: MockClient(
        (_) async =>
            http.Response(jsonEncode({'detail': 'Unknown workflow.'}), 400),
      ),
    );

    expect(
      () => client.getLatestTrace('w9'),
      throwsA(
        isA<ApiException>().having(
          (e) => e.message,
          'message',
          'Unknown workflow.',
        ),
      ),
    );
    client.close();
  });

  test('non-JSON errors fall back to a generic message', () async {
    final client = MusePilotApi(
      baseUrl: 'http://test',
      client: MockClient((_) async => http.Response('boom', 500)),
    );

    expect(() => client.getBenchmark(), throwsA(isA<ApiException>()));
    client.close();
  });

  test('frame URLs carry workflow, state, and trace parameters', () {
    final client = MusePilotApi(baseUrl: 'http://test:8501');
    final url = client.somFrameUrl(
      workflow: 'w2',
      state: 'step_2_modal_blocked',
      traceId: 'abc',
    );
    expect(url, contains('/api/frames/som'));
    expect(url, contains('workflow=w2'));
    expect(url, contains('state=step_2_modal_blocked'));
    expect(url, contains('trace_id=abc'));
    client.close();
  });
}
