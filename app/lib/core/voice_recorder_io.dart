// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Microphone capture for IO platforms (Android, iOS, macOS, Windows).
library;

import 'dart:io';
import 'dart:typed_data';

import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

import 'voice_recorder_api.dart';

/// Records a WAV clip into a temp file, then returns its bytes.
class PlatformVoiceRecorder implements VoiceRecorder {
  final AudioRecorder _recorder = AudioRecorder();

  String? _path;

  @override
  bool get isSupported => true;

  @override
  Future<bool> hasPermission() => _recorder.hasPermission();

  @override
  Future<void> start() async {
    final dir = await getTemporaryDirectory();
    _path = '${dir.path}/musepilot_command.wav';
    await _recorder.start(
      const RecordConfig(encoder: AudioEncoder.wav),
      path: _path!,
    );
  }

  @override
  Future<Uint8List?> stop() async {
    final out = await _recorder.stop();
    final file = File(out ?? _path ?? '');
    if (await file.exists()) {
      final bytes = await file.readAsBytes();
      await file.delete();
      return bytes;
    }
    return null;
  }

  @override
  Future<void> dispose() => _recorder.dispose();
}
