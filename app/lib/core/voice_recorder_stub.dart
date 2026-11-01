// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Fallback voice recorder for platforms without microphone capture.
library;

import 'dart:typed_data';

import 'voice_recorder_api.dart';

/// Reports unsupported; used where no platform implementation applies.
class PlatformVoiceRecorder implements VoiceRecorder {
  @override
  bool get isSupported => false;

  @override
  Future<bool> hasPermission() async => false;

  @override
  Future<void> start() async {
    throw UnsupportedError(
      'Voice recording is not supported on this platform.',
    );
  }

  @override
  Future<Uint8List?> stop() async => null;

  @override
  Future<void> dispose() async {}
}
