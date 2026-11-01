// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Microphone capture contract for voice intake.
library;

import 'dart:typed_data';

/// Records a WAV clip from the microphone.
///
/// Platform implementations live behind `voice_recorder.dart` conditional
/// exports; unsupported platforms report [isSupported] as false instead of
/// throwing at construction time.
abstract class VoiceRecorder {
  /// Whether this platform can capture microphone audio.
  bool get isSupported;

  /// Checks (and requests) microphone permission.
  Future<bool> hasPermission();

  /// Starts recording a mono WAV clip.
  Future<void> start();

  /// Stops recording and returns the WAV bytes, or null when empty.
  Future<Uint8List?> stop();

  /// Releases recorder resources.
  Future<void> dispose();
}
