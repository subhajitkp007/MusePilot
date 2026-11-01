// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Voice recorder entry point with per-platform implementations.
library;

export 'voice_recorder_api.dart';
export 'voice_recorder_stub.dart'
    if (dart.library.io) 'voice_recorder_io.dart'
    if (dart.library.js_interop) 'voice_recorder_web.dart';
