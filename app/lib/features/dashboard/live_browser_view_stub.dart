// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Stub implementation for non-web platforms and tests.
library;

import 'package:flutter/material.dart';

import '../../../theme/meta_theme.dart';

/// Opens the specified URL in the system browser.
void openExternalUrl(String url) {
  // Non-web fallback (e.g. CLI or headless test)
}

/// Fallback widget when running outside a web browser.
class LiveBrowserWidget extends StatelessWidget {
  const LiveBrowserWidget({
    required this.url,
    this.title = 'TradingView BTC/USD Market Terminal',
    super.key,
  });

  final String url;
  final String title;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFF131722),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.candlestick_chart,
              size: 48,
              color: MetaTheme.metaBlue,
            ),
            const SizedBox(height: 12),
            Text(
              title,
              style: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 6),
            const Text(
              'Live Interactive TradingView Chart available on Web HUD',
              style: TextStyle(
                fontSize: 12,
                color: MetaTheme.inkSecondary,
              ),
            ),
            const SizedBox(height: 12),
            SelectableText(
              url,
              style: const TextStyle(
                fontSize: 11,
                fontFamily: 'monospace',
                color: MetaTheme.metaBlueDark,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

