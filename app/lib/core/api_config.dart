// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// API endpoint configuration with build-time override support.
library;

/// Resolves the HUD API base URL.
///
/// Override at build/run time for phones and remote servers:
/// `flutter run --dart-define=MUSEPILOT_API_BASE=http://192.168.1.10:8501`
class ApiConfig {
  /// Localhost default for desktop simulators, browsers, and macOS.
  static const String defaultBaseUrl = 'http://localhost:8501';

  /// Build-time base URL from `--dart-define=MUSEPILOT_API_BASE`.
  static String baseUrlFromEnv() => const String.fromEnvironment(
    'MUSEPILOT_API_BASE',
    defaultValue: defaultBaseUrl,
  );

  /// Derive the run-streaming WebSocket URL from an HTTP(S) base URL.
  static String wsRunsUrl(String baseUrl) =>
      '${baseUrl.replaceFirst(RegExp('^http'), 'ws')}/ws/runs';
}
