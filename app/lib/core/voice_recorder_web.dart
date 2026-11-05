// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Microphone capture for Flutter web via the browser MediaRecorder.
library;

import 'dart:js_interop';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:record/record.dart';
import 'package:web/web.dart' as web;

import 'voice_recorder_api.dart';

/// Records a WAV clip; the blob URL from [stop] is fetched into bytes.
class PlatformVoiceRecorder implements VoiceRecorder {
  final AudioRecorder _recorder = AudioRecorder();
  final http.Client _client = http.Client();

  @override
  bool get isSupported => true;

  @override
  Future<bool> hasPermission() async {
    try {
      return await _recorder.hasPermission();
    } catch (_) {
      try {
        final mediaDevices = web.window.navigator.mediaDevices;
        final constraints = web.MediaStreamConstraints(audio: true.toJS);
        final stream = await mediaDevices.getUserMedia(constraints).toDart;
        final tracks = stream.getAudioTracks().toDart;
        for (var i = 0; i < tracks.length; i++) {
          tracks[i].stop();
        }
        return true;
      } catch (_) {
        return false;
      }
    }
  }

  @override
  Future<void> start() async {
    try {
      await _recorder.start(
        const RecordConfig(encoder: AudioEncoder.wav),
        path: 'command.wav',
      );
    } catch (_) {
      try {
        await _recorder.start(
          const RecordConfig(encoder: AudioEncoder.opus),
          path: 'command.opus',
        );
      } catch (_) {
        await _recorder.start(
          const RecordConfig(encoder: AudioEncoder.aacLc),
          path: 'command.m4a',
        );
      }
    }
  }

  @override
  Future<Uint8List?> stop() async {
    final url = await _recorder.stop();
    if (url == null) return null;
    try {
      final response = await _client.get(Uri.parse(url));
      if (response.statusCode == 200 && response.bodyBytes.isNotEmpty) {
        return response.bodyBytes;
      }
    } catch (_) {
      // http.Client may be restricted on blob: URLs in some browser sandboxes; fall back to browser fetch API.
    }
    try {
      final resp = await web.window.fetch(url.toJS).toDart;
      final arrayBuffer = await resp.arrayBuffer().toDart;
      return arrayBuffer.toDart.asUint8List();
    } catch (_) {
      return null;
    }
  }

  @override
  Future<void> dispose() async {
    _client.close();
    await _recorder.dispose();
  }
}
