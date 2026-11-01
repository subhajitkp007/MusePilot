// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Microphone capture for Flutter web via the browser MediaRecorder.
library;

import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:record/record.dart';

import 'voice_recorder_api.dart';

/// Records a WAV clip; the blob URL from [stop] is fetched into bytes.
class PlatformVoiceRecorder implements VoiceRecorder {
  final AudioRecorder _recorder = AudioRecorder();
  final http.Client _client = http.Client();

  @override
  bool get isSupported => true;

  @override
  Future<bool> hasPermission() => _recorder.hasPermission();

  @override
  Future<void> start() async {
    // The path is ignored on web; stop() returns a blob URL instead.
    await _recorder.start(
      const RecordConfig(encoder: AudioEncoder.wav),
      path: 'command.wav',
    );
  }

  @override
  Future<Uint8List?> stop() async {
    final url = await _recorder.stop();
    if (url == null) return null;
    final response = await _client.get(Uri.parse(url));
    if (response.statusCode != 200) return null;
    return response.bodyBytes;
  }

  @override
  Future<void> dispose() async {
    _client.close();
    await _recorder.dispose();
  }
}
