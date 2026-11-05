// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Web implementation embedding live interactive TradingView HTML5 chart inside Flutter Web.
library;

// ignore_for_file: avoid_web_libraries_in_flutter
import 'dart:js_interop';
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
    this.currentState = 'initial',
    super.key,
  });

  final String url;
  final String title;
  final String currentState;

  @override
  State<LiveBrowserWidget> createState() => _LiveBrowserWidgetState();
}

class _LiveBrowserWidgetState extends State<LiveBrowserWidget> {
  late final String _viewType;

  @override
  void initState() {
    super.initState();
    _viewType = 'tv-iframe-${widget.url.hashCode.abs()}';
    _ensureIframeRegistered(_viewType, widget.url);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _notifyIframe(widget.currentState);
    });
  }

  @override
  void didUpdateWidget(LiveBrowserWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.currentState != widget.currentState) {
      _notifyIframe(widget.currentState);
    }
  }

  void _notifyIframe(String state) {
    try {
      final iframes = web.document.querySelectorAll('iframe');
      for (var i = 0; i < iframes.length; i++) {
        final iframe = iframes.item(i) as web.HTMLIFrameElement?;
        if (iframe != null &&
            (iframe.src.contains('tradingview_live') ||
                iframe.src.contains('tv-iframe'))) {
          iframe.contentWindow?.postMessage(
            {'type': 'MUSEPILOT_STEP', 'state': state}.jsify(),
            '*'.toJS,
          );
        }
      }
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return HtmlElementView(viewType: _viewType);
  }
}


