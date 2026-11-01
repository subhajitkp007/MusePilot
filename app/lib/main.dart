// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// MusePilot cross-platform HUD entry point.
library;

import 'package:flutter/material.dart';

import 'features/dashboard/dashboard_screen.dart';
import 'theme/meta_theme.dart';

void main() => runApp(const MusePilotApp());

/// Root application widget with Meta light/dark themes.
class MusePilotApp extends StatelessWidget {
  const MusePilotApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'MusePilot Console',
    debugShowCheckedModeBanner: false,
    theme: MetaTheme.light(),
    darkTheme: MetaTheme.dark(),
    // The console is a dark-first ops surface; light() stays available
    // for embedders that opt into it.
    themeMode: ThemeMode.dark,
    home: const DashboardScreen(),
  );
}
