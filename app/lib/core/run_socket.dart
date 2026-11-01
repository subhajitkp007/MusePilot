// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Live run-progress stream over the `/ws/runs` WebSocket.
library;

import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

import '../models/trace.dart';

/// Base type for run-stream events.
sealed class RunEvent {
  const RunEvent();
}

/// The server accepted the run request.
class RunStarted extends RunEvent {
  const RunStarted(this.workflowId);

  final String workflowId;
}

/// A telemetry span completed (perception, planning, dispatch, verify).
class RunSpanEvent extends RunEvent {
  const RunSpanEvent(this.span);

  final Map<String, dynamic> span;
}

/// A live step execution record completed and verified during run.
class RunStepRecordEvent extends RunEvent {
  const RunStepRecordEvent(this.record);

  final StepExecutionRecord record;
}

/// The run finished; carries the full deterministic trace.
class RunCompleted extends RunEvent {
  const RunCompleted(this.trace);

  final RunTrace trace;
}

/// The run failed before producing a trace.
class RunFailed extends RunEvent {
  const RunFailed(this.detail);

  final String detail;
}

/// Opens a run stream and translates socket messages into [RunEvent]s.
class RunSocket {
  /// Stream live progress for one workflow execution.
  static Stream<RunEvent> run({
    required String wsUrl,
    required String workflowId,
    required bool injectModal,
    String driver = 'simulated',
    String? customIntent,
  }) async* {
    late WebSocketChannel channel;
    try {
      channel = WebSocketChannel.connect(Uri.parse(wsUrl));
    } on Exception catch (e) {
      yield RunFailed('Cannot open run stream ($e).');
      return;
    }
    final payload = <String, dynamic>{
      'workflow_id': workflowId,
      'inject_modal': injectModal,
      'driver': driver,
    };
    if (customIntent != null && customIntent.trim().isNotEmpty) {
      payload['custom_intent'] = customIntent.trim();
    }
    channel.sink.add(jsonEncode(payload));
    try {
      await for (final message in channel.stream) {
        final decoded = jsonDecode(message as String);
        if (decoded is! Map<String, dynamic>) {
          yield const RunFailed('Received a malformed stream message.');
          break;
        }
        switch (decoded['type']) {
          case 'started':
            yield RunStarted(decoded['workflow_id'] as String? ?? workflowId);
          case 'span':
            yield RunSpanEvent(
              Map<String, dynamic>.from(decoded['span'] as Map? ?? {}),
            );
          case 'step_record':
            yield RunStepRecordEvent(
              StepExecutionRecord.fromJson(
                Map<String, dynamic>.from(decoded['record'] as Map? ?? {}),
              ),
            );
          case 'complete':
            yield RunCompleted(
              RunTrace.fromJson(decoded['trace'] as Map<String, dynamic>),
            );
            await channel.sink.close();
            return;
          case 'error':
            yield RunFailed(decoded['detail'] as String? ?? 'Run failed.');
            await channel.sink.close();
            return;
        }
      }
    } on FormatException {
      yield const RunFailed('Received a malformed stream message.');
    } on Exception catch (e) {
      yield RunFailed('Run stream dropped ($e).');
    } finally {
      await channel.sink.close();
    }
  }
}
