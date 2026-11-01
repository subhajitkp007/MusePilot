// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// API endpoint configuration with build-time override support.
library;

import 'package:flutter/foundation.dart';

/// Resolves the HUD API base URL.
///
/// Override at build/run time for phones and remote servers:
/// `flutter run --dart-define=MUSEPILOT_API_BASE=http://192.168.1.10:8501`
class ApiConfig {
  /// Localhost default for desktop simulators, browsers, and macOS.
  static const String defaultBaseUrl = 'http://localhost:8501';

  /// Dynamically detect the browser origin when running on Flutter Web,
  /// falling back to build-time override or default localhost.
  static String baseUrlFromEnv() {
    const fromEnv = String.fromEnvironment('MUSEPILOT_API_BASE');
    if (fromEnv.isNotEmpty) return fromEnv;
    if (kIsWeb) {
      final origin = Uri.base.origin;
      if (origin.startsWith('http://') || origin.startsWith('https://')) {
        return origin;
      }
    }
    return defaultBaseUrl;
  }

  /// Derive the run-streaming WebSocket URL from an HTTP(S) base URL.
  static String wsRunsUrl(String baseUrl) =>
      '${baseUrl.replaceFirst(RegExp('^http'), 'ws')}/ws/runs';
}
