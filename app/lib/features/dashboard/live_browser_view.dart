// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Platform-adaptive live browser view component.
library;

export 'live_browser_view_stub.dart'
    if (dart.library.js_interop) 'live_browser_view_web.dart';
