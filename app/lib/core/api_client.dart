// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Typed REST client for the MusePilot HUD API.
library;

import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../models/benchmark.dart';
import '../models/server.dart';
import '../models/trace.dart';

/// Structured API failure surfaced to the HUD.
class ApiException implements Exception {
  ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => 'ApiException(${statusCode ?? '?'}): $message';
}

/// State-timeline payload for the SoM viewer.
class StateTimeline {
  const StateTimeline({required this.states, required this.defaultState});

  factory StateTimeline.fromJson(Map<String, dynamic> json) {
    final states = (json['states'] as List? ?? ['initial'])
        .map((s) => s.toString())
        .toList();
    return StateTimeline(
      states: states,
      defaultState: json['default_state'] as String? ?? states.last,
    );
  }

  final List<String> states;
  final String defaultState;
}

/// Thin typed wrapper over the Starlette HUD endpoints.
class MusePilotApi {
  MusePilotApi({required this.baseUrl, http.Client? client})
    : _client = client ?? http.Client();

  final String baseUrl;
  final http.Client _client;
  String? _authToken;

  /// Explicitly seed or update the bearer authorization token.
  void setAuthToken(String? token) {
    _authToken = token;
  }

  /// Automatically negotiate session bearer token from the server.
  Future<String?> ensureAuthenticated() async {
    if (_authToken != null) return _authToken;
    try {
      final res = await _client
          .get(_uri('/api/auth/token'))
          .timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        final body = jsonDecode(res.body);
        if (body is Map && body['token'] is String) {
          _authToken = body['token'] as String;
          return _authToken;
        }
      }
    } catch (_) {
      // Ignore in offline / test environments with mock transports.
    }
    return null;
  }

  Uri _uri(String path, [Map<String, String>? query]) =>
      Uri.parse('$baseUrl$path').replace(queryParameters: query);

  Future<dynamic> _getJson(String path, [Map<String, String>? query]) async {
    late http.Response response;
    final headers = <String, String>{};
    if (_authToken != null) headers['Authorization'] = 'Bearer $_authToken';
    try {
      response = await _client
          .get(_uri(path, query), headers: headers.isEmpty ? null : headers)
          .timeout(const Duration(seconds: 30));
    } on TimeoutException {
      throw ApiException('Request to $path timed out.', statusCode: 408);
    } on Exception catch (e) {
      throw ApiException('Cannot reach $baseUrl ($e).');
    }
    return _decode(response, path);
  }

  dynamic _decode(http.Response response, String path) {
    if (response.statusCode < 200 || response.statusCode >= 300) {
      String detail = 'Request to $path failed.';
      try {
        final body = jsonDecode(response.body);
        if (body is Map && body['detail'] is String) {
          detail = body['detail'] as String;
        }
      } on FormatException {
        // Keep the generic detail when the error body is not JSON.
      }
      throw ApiException(detail, statusCode: response.statusCode);
    }
    return jsonDecode(response.body);
  }

  /// Fetch the pre-flight readiness report.
  Future<HealthReport> getHealth() async {
    await ensureAuthenticated();
    return HealthReport.fromJson(
      await _getJson('/api/health') as Map<String, dynamic>,
    );
  }

  /// Fetch non-secret runtime configuration.
  Future<ServerConfig> getConfig() async => ServerConfig.fromJson(
    await _getJson('/api/config') as Map<String, dynamic>,
  );

  /// List the frozen demo workflows.
  Future<List<WorkflowInfo>> listWorkflows() async {
    final body = await _getJson('/api/workflows') as List;
    return body
        .map((w) => WorkflowInfo.fromJson(w as Map<String, dynamic>))
        .toList();
  }

  /// Execute a workflow synchronously and return its full trace.
  Future<RunTrace> createRun({
    required String workflowId,
    required bool injectModal,
    String driver = 'simulated',
    String? customIntent,
  }) async {
    late http.Response response;
    final payload = <String, Object?>{
      'workflow_id': workflowId,
      'inject_modal': injectModal,
      'driver': driver,
    };
    if (customIntent != null) payload['custom_intent'] = customIntent;
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (_authToken != null) headers['Authorization'] = 'Bearer $_authToken';
    try {
      response = await _client
          .post(
            _uri('/api/runs'),
            headers: headers,
            body: jsonEncode(payload),
          )
          .timeout(const Duration(seconds: 120));
    } on TimeoutException {
      throw ApiException('Run request timed out.', statusCode: 408);
    } on Exception catch (e) {
      throw ApiException('Cannot reach $baseUrl ($e).');
    }
    return RunTrace.fromJson(
      _decode(response, '/api/runs') as Map<String, dynamic>,
    );
  }

  /// List recent run-trace summaries, newest first.
  Future<List<TraceSummary>> listTraces({int limit = 20}) async {
    final body = await _getJson('/api/traces', {'limit': '$limit'}) as List;
    return body
        .map((t) => TraceSummary.fromJson(t as Map<String, dynamic>))
        .toList();
  }

  /// Fetch the golden or latest trace for a workflow.
  Future<RunTrace> getLatestTrace(String workflowId) async => RunTrace.fromJson(
    await _getJson('/api/traces/latest/$workflowId') as Map<String, dynamic>,
  );

  /// Fetch a single trace by ID.
  Future<RunTrace> getTrace(String traceId) async => RunTrace.fromJson(
    await _getJson('/api/traces/$traceId') as Map<String, dynamic>,
  );

  /// Fetch the visual-state timeline for the SoM viewer.
  Future<StateTimeline> getStates({
    required String workflow,
    String? traceId,
  }) async {
    final query = <String, String>{'workflow': workflow};
    if (traceId != null) query['trace_id'] = traceId;
    return StateTimeline.fromJson(
      await _getJson('/api/states', query) as Map<String, dynamic>,
    );
  }

  /// Fetch the cumulative benchmark report.
  Future<BenchmarkReport> getBenchmark() async => BenchmarkReport.fromJson(
    await _getJson('/api/benchmark') as Map<String, dynamic>,
  );

  /// Transcribe a WAV voice command via Meta Muse Voice Transcribe.
  ///
  /// The server accepts multipart form data: field `audio` (WAV bytes) and
  /// field `workflow_id`. In live mode this calls the Meta ASR API; in
  /// simulated mode the server returns a calibrated fixture transcript.
  Future<VoiceTranscript> transcribeAudio({
    required Uint8List audioBytes,
    String filename = 'command.wav',
    String workflowId = 'w2',
  }) async {
    await ensureAuthenticated();
    final request = http.MultipartRequest(
      'POST',
      _uri('/api/voice/transcribe'),
    );
    if (_authToken != null) {
      request.headers['Authorization'] = 'Bearer $_authToken';
    }
    request.fields['workflow_id'] = workflowId;
    request.files.add(
      http.MultipartFile.fromBytes('audio', audioBytes, filename: filename),
    );
    late http.StreamedResponse streamed;
    try {
      streamed = await _client
          .send(request)
          .timeout(const Duration(seconds: 120));
    } on TimeoutException {
      throw ApiException(
        'Voice transcribe request timed out.',
        statusCode: 408,
      );
    } on Exception catch (e) {
      throw ApiException('Cannot reach $baseUrl ($e).');
    }
    final response = await http.Response.fromStream(streamed);
    return VoiceTranscript.fromJson(
      _decode(response, '/api/voice/transcribe') as Map<String, dynamic>,
    );
  }

  /// Build a raw-frame image URL (traceId busts the image cache per run).
  String rawFrameUrl({
    required String workflow,
    required String state,
    String? traceId,
  }) {
    final query = <String, String>{'workflow': workflow, 'state': state};
    if (traceId != null) query['trace_id'] = traceId;
    return _uri('/api/frames/raw', query).toString();
  }

  /// Build a Set-of-Mark overlay image URL.
  String somFrameUrl({
    required String workflow,
    required String state,
    String? traceId,
  }) {
    final query = <String, String>{'workflow': workflow, 'state': state};
    if (traceId != null) query['trace_id'] = traceId;
    return _uri('/api/frames/som', query).toString();
  }

  /// Build a live target preview frame URL.
  String liveFrameUrl({
    String driver = 'adb',
    String? serial,
    String format = 'jpeg',
  }) {
    final query = <String, String>{
      'driver': driver,
      'format': format,
      't': DateTime.now().millisecondsSinceEpoch.toString(),
    };
    if (serial != null) query['serial'] = serial;
    return _uri('/api/frames/live', query).toString();
  }

  /// Release the underlying HTTP client.
  void close() => _client.close();
}
