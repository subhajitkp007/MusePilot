// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Web implementation embedding live interactive TradingView HTML5 chart inside Flutter Web.
library;

// ignore_for_file: avoid_web_libraries_in_flutter
import 'dart:ui_web' as ui_web;

import 'package:flutter/material.dart';
import 'package:web/web.dart' as web;

final Set<String> _registeredViews = <String>{};

/// Opens an external URL in a new browser tab.
void openExternalUrl(String url) {
  try {
    web.window.open(url, '_blank');
  } catch (_) {}
}

/// Registers an iframe view factory if not already registered.
void _ensureIframeRegistered(String viewType, String url) {
  if (_registeredViews.contains(viewType)) return;
  _registeredViews.add(viewType);

  ui_web.platformViewRegistry.registerViewFactory(
    viewType,
    (int viewId) {
      final iframe = web.HTMLIFrameElement();
      iframe.src = url;
      iframe.style.border = 'none';
      iframe.style.width = '100%';
      iframe.style.height = '100%';
      iframe.setAttribute('allow', 'fullscreen');
      return iframe;
    },
  );
}

/// Embedded live web browser widget rendering an interactive HTML5 iframe.
class LiveBrowserWidget extends StatefulWidget {
  const LiveBrowserWidget({
    required this.url,
    this.title = 'TradingView BTC/USD Market Terminal',
    super.key,
  });

  final String url;
  final String title;

  @override
  State<LiveBrowserWidget> createState() => _LiveBrowserWidgetState();
}

class _LiveBrowserWidgetState extends State<LiveBrowserWidget> {
  late final String _viewType;

  @override
  void initState() {
    super.initState();
    // Unique view type per URL to avoid iframe cache collisions
    _viewType = 'tv-iframe-${widget.url.hashCode.abs()}';
    _ensureIframeRegistered(_viewType, widget.url);
  }

  @override
  Widget build(BuildContext context) {
    return HtmlElementView(viewType: _viewType);
  }
}
