// Copyright 2026 MusePilot Authors
// Licensed under the Apache License, Version 2.0
/// Professional Meta Enterprise SaaS HUD with Navigation Rail, Editable Chat Intent & SDK Drawer.
library;

import 'package:flutter/material.dart';

import '../../../core/api_client.dart';
import '../../../core/api_config.dart';
import '../../../core/run_socket.dart';
import '../../../models/benchmark.dart';
import '../../../models/server.dart';
import '../../../models/trace.dart';
import '../../../theme/meta_theme.dart';
import 'benchmark_panel.dart';
import 'connection_bar.dart';
import 'developer_hub_view.dart';
import 'fleet_manager_view.dart';
import 'governance_view.dart';
import 'hackathon_banner.dart';
import 'history_panel.dart';
import 'ledger_panel.dart';
import 'metrics_row.dart';
import 'run_panel.dart';
import 'solution_showcase_bar.dart';
import 'som_viewer.dart';
import 'step_graph_view.dart';
import 'terminal_drawer.dart';

/// Single-screen Mission Control HUD composing every dashboard section.
class DashboardScreen extends StatefulWidget {
  const DashboardScreen({MusePilotApi? api, super.key}) : _apiOverride = api;

  final MusePilotApi? _apiOverride;

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  late MusePilotApi _api;
  late String _baseUrl;
  bool _ownsApi = true;

  int _selectedNavIndex = 0;
  bool _refreshing = true;
  bool _running = false;
  String? _error;

  HealthReport? _health;
  List<WorkflowInfo> _workflows = const [];
  String _workflow = 'w1';
  bool _injectModal = false;
  String _driver = 'simulated';
  String _selectedScenarioId = kSolutionScenarios.first.id;

  late final TextEditingController _intentController;

  RunTrace? _trace;
  List<Map<String, dynamic>> _spans = const [];
  List<String> _states = const ['initial'];
  String _state = 'initial';
  List<StepExecutionRecord> _liveRecords = const [];
  BenchmarkReport? _benchmark;
  List<TraceSummary> _history = const [];
  ServerConfig? _config;
  bool _showTerminal = false;

  @override
  void initState() {
    super.initState();
    _baseUrl = ApiConfig.baseUrlFromEnv();
    _intentController = TextEditingController(
      text: kSolutionScenarios.first.defaultIntent,
    );

    if (widget._apiOverride != null) {
      _api = widget._apiOverride!;
      _ownsApi = false;
    } else {
      _api = MusePilotApi(baseUrl: _baseUrl);
    }
    _refresh();
  }

  @override
  void dispose() {
    _intentController.dispose();
    if (_ownsApi) _api.close();
    super.dispose();
  }

  void _fail(String message) {
    if (!mounted) return;
    setState(() => _error = message);
  }

  /// Reload health, latest trace, timeline, benchmark, and history.
  Future<void> _refresh() async {
    setState(() {
      _refreshing = true;
      _error = null;
    });
    try {
      final health = await _api.getHealth();
      final config = await _api.getConfig();
      final workflows = await _api.listWorkflows();
      RunTrace? trace;
      try {
        trace = await _api.getLatestTrace(_workflow);
      } on ApiException catch (e) {
        if (e.statusCode != 404) rethrow;
      }
      final timeline = await _api.getStates(
        workflow: _workflow,
        traceId: trace?.traceId,
      );
      final benchmark = await _api.getBenchmark();
      final history = await _api.listTraces(limit: 10);
      if (!mounted) return;
      setState(() {
        _health = health;
        _config = config;
        _workflows = workflows;
        _trace = trace;
        _states = timeline.states;
        _state = timeline.defaultState;
        _benchmark = benchmark;
        _history = history;
      });
    } on ApiException catch (e) {
      _fail(e.message);
    } finally {
      if (mounted) setState(() => _refreshing = false);
    }
  }

  /// Handle industry scenario click.
  void _onSelectScenario(SolutionScenario scenario) {
    setState(() {
      _selectedScenarioId = scenario.id;
      _workflow = scenario.workflowId;
      _injectModal = scenario.injectModal;
      _intentController.text = scenario.defaultIntent;
      _driver = (scenario.id == 'mobile_adb' ? 'adb' : 'simulated');
    });
    _refresh();
  }

  /// Execute the selected workflow over the live run stream.
  Future<void> _run() async {
    final customIntent = _intentController.text.trim();
    setState(() {
      _running = true;
      _error = null;
      _spans = const [];
      _liveRecords = const [];
    });
    final feed = <Map<String, dynamic>>[];
    try {
      await for (final event in RunSocket.run(
        wsUrl: ApiConfig.wsRunsUrl(_baseUrl),
        workflowId: _workflow,
        injectModal: _injectModal,
        driver: _driver,
        customIntent: customIntent.isNotEmpty ? customIntent : null,
      )) {
        if (!mounted) return;
        switch (event) {
          case RunStarted():
            // The server acknowledges the run; telemetry below only ever
            // shows spans the server actually emitted.
            break;
          case RunSpanEvent(:final span):
            feed.add(span);
            setState(() => _spans = List.of(feed));
          case RunStepRecordEvent(:final record):
            setState(() {
              _liveRecords = [..._liveRecords, record];
            });
          case RunCompleted(:final trace):
            await _adoptTrace(trace);
            if (!mounted) return;
            final passed = trace.records.where((r) => r.verdict.passed).length;
            final total = trace.records.length;
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(
                  total == 0
                      ? 'Run completed with no executed steps.'
                      : passed == total
                      ? 'Run completed: $passed of $total steps verified.'
                      : 'Run completed with failures: $passed of $total steps verified.',
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
            );
          case RunFailed(:final detail):
            _fail(detail);
        }
      }
    } on Exception catch (e) {
      _fail('Run failed ($e).');
    } finally {
      if (mounted) setState(() => _running = false);
    }
  }

  /// Adopt a fresh trace and reload dependent sections.
  Future<void> _adoptTrace(RunTrace trace) async {
    try {
      final timeline = await _api.getStates(
        workflow: trace.workflowId,
        traceId: trace.traceId,
      );
      final benchmark = await _api.getBenchmark();
      final history = await _api.listTraces(limit: 10);
      if (!mounted) return;
      setState(() {
        _trace = trace;
        _workflow = trace.workflowId;
        _states = timeline.states;
        _state = timeline.defaultState;
        _benchmark = benchmark;
        _history = history;
      });
    } on ApiException catch (e) {
      _fail(e.message);
    }
  }

  /// Load a historical trace from the history list.
  Future<void> _loadTrace(String traceId) async {
    setState(() => _refreshing = true);
    try {
      final trace = await _api.getTrace(traceId);
      await _adoptTrace(trace);
    } on ApiException catch (e) {
      _fail(e.message);
    } finally {
      if (mounted) setState(() => _refreshing = false);
    }
  }

  /// Re-point the HUD at another API server.
  void _applyBaseUrl(String baseUrl) {
    final normalized = baseUrl.trim().replaceAll(RegExp(r'/+$'), '');
    if (normalized.isEmpty || normalized == _baseUrl) return;
    if (_ownsApi) _api.close();
    setState(() {
      _baseUrl = normalized;
      _api = MusePilotApi(baseUrl: normalized);
      _ownsApi = true;
      _trace = null;
      _health = null;
      _config = null;
    });
    _refresh();
  }

  /// Short model name for badges, e.g. `meta-models/sam-3.1` -> `sam-3.1`.
  String _shortModel(String id) {
    if (id.isEmpty) return 'unknown';
    return id.split('/').last;
  }

  String _targetLabel() {
    switch (_driver) {
      case 'adb':
        final available = _health?.adbAvailable ?? false;
        return available ? 'Target: ADB device' : 'Target: ADB (no device)';
      case 'desktop':
        return 'Target: Desktop';
      default:
        return 'Target: Simulated';
    }
  }

  @override
  Widget build(BuildContext context) {
    final health = _health;
    final ready = health?.passed ?? false;
    final adbSelected = _driver == 'adb';
    final adbOk = health?.adbAvailable ?? false;
    return Scaffold(
      appBar: AppBar(
        toolbarHeight: 60,
        backgroundColor: MetaTheme.surfaceCard,
        elevation: 0,
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(7),
              decoration: BoxDecoration(
                color: MetaTheme.metaBlue,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.hub, size: 20, color: Colors.white),
            ),
            const SizedBox(width: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Text(
                      'MusePilot',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                        color: MetaTheme.inkPrimary,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 6,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: MetaTheme.metaBlue.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(
                          color: MetaTheme.metaBlue.withValues(alpha: 0.5),
                        ),
                      ),
                      child: const Text(
                        'Console',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          color: MetaTheme.metaBlueDark,
                        ),
                      ),
                    ),
                  ],
                ),
                const Text(
                  'Visual automation with Meta SAM 3.1 and Muse Spark',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w500,
                    color: MetaTheme.inkSecondary,
                  ),
                ),
              ],
            ),
          ],
        ),
        actions: [
          if (health != null) ...[
            _appBarBadge(
              icon: Icons.blur_on,
              label: _shortModel(health.samModelId),
              color: MetaTheme.metaBlueDark,
            ),
            const SizedBox(width: 8),
            _appBarBadge(
              icon: Icons.verified_user,
              label:
                  _config?.verifierDisplayName ??
                  _shortModel(health.verifierModelId),
              color: MetaTheme.emeraldVerified,
            ),
            const SizedBox(width: 8),
            _appBarBadge(
              icon: adbSelected
                  ? Icons.phone_android
                  : _driver == 'desktop'
                  ? Icons.desktop_windows
                  : Icons.science,
              label: _targetLabel(),
              color: adbSelected && !adbOk
                  ? MetaTheme.amberWarning
                  : MetaTheme.inkSecondary,
            ),
            const SizedBox(width: 8),
          ],
          _appBarBadge(
            icon: Icons.favorite,
            label: health == null
                ? 'Connecting'
                : ready
                ? 'Ready'
                : 'Degraded',
            color: health == null
                ? MetaTheme.inkSecondary
                : ready
                ? MetaTheme.emeraldVerified
                : MetaTheme.coralAlert,
          ),
          const SizedBox(width: 16),
        ],
      ),
      body: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Meta Enterprise Left Navigation Rail
          Column(
            children: [
              Expanded(
                child: NavigationRail(
                  selectedIndex: _selectedNavIndex,
                  backgroundColor: MetaTheme.surfaceCard,
                  minWidth: 72,
                  groupAlignment: -0.9,
                  labelType: NavigationRailLabelType.all,
                  selectedLabelTextStyle: const TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    color: MetaTheme.metaBlueDark,
                  ),
                  unselectedLabelTextStyle: const TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                    color: MetaTheme.inkSecondary,
                  ),
                  selectedIconTheme: const IconThemeData(
                    color: MetaTheme.metaBlueDark,
                    size: 22,
                  ),
                  unselectedIconTheme: const IconThemeData(
                    color: MetaTheme.inkSecondary,
                    size: 20,
                  ),
                  onDestinationSelected: (index) =>
                      setState(() => _selectedNavIndex = index),
                  destinations: const [
                    NavigationRailDestination(
                      icon: Icon(Icons.dashboard_outlined),
                      selectedIcon: Icon(Icons.dashboard),
                      label: Text('Mission'),
                    ),
                    NavigationRailDestination(
                      icon: Icon(Icons.devices_other_outlined),
                      selectedIcon: Icon(Icons.devices_other),
                      label: Text('Fleet'),
                    ),
                    NavigationRailDestination(
                      icon: Icon(Icons.integration_instructions_outlined),
                      selectedIcon: Icon(Icons.integration_instructions),
                      label: Text('SDK Hub'),
                    ),
                    NavigationRailDestination(
                      icon: Icon(Icons.shield_outlined),
                      selectedIcon: Icon(Icons.shield),
                      label: Text('Trust'),
                    ),
                    NavigationRailDestination(
                      icon: Icon(Icons.analytics_outlined),
                      selectedIcon: Icon(Icons.analytics),
                      label: Text('Metrics'),
                    ),
                  ],
                ),
              ),

              // Bottom Terminal & Settings Action Icons
              Container(
                width: 72,
                color: MetaTheme.surfaceCard,
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Column(
                  children: [
                    IconButton(
                      tooltip: 'Cloud Shell Terminal',
                      icon: Icon(
                        _showTerminal ? Icons.terminal : Icons.terminal_outlined,
                        color: _showTerminal ? MetaTheme.electricCyan : MetaTheme.inkSecondary,
                        size: 20,
                      ),
                      onPressed: () => setState(() => _showTerminal = !_showTerminal),
                    ),
                    const SizedBox(height: 4),
                    IconButton(
                      tooltip: 'System Settings',
                      icon: const Icon(
                        Icons.settings_outlined,
                        color: MetaTheme.inkSecondary,
                        size: 20,
                      ),
                      onPressed: () {
                        setState(() => _selectedNavIndex = 2); // Jump to SDK Hub & Infrastructure Gateway
                      },
                    ),
                  ],
                ),
              ),
            ],
          ),
          const VerticalDivider(
            width: 1,
            thickness: 1,
            color: MetaTheme.surfaceCardBorder,
          ),

          // Main Content View
          Expanded(
            child: Column(
              children: [
                Expanded(
                  child: SingleChildScrollView(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                  // Integration banner: configured Meta models and drivers.
                  HackathonBanner(
                    verifierLabel: _config?.verifierDisplayName ?? 'Verifier',
                  ),

                  if (_error != null)
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 14,
                          vertical: 10,
                        ),
                        decoration: BoxDecoration(
                          color: MetaTheme.coralAlert.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: MetaTheme.coralAlert),
                        ),
                        child: Row(
                          children: [
                            const Icon(
                              Icons.error_outline,
                              color: MetaTheme.coralAlert,
                              size: 18,
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                _error!,
                                style: const TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                  color: MetaTheme.coralAlert,
                                ),
                              ),
                            ),
                            IconButton(
                              icon: const Icon(
                                Icons.close,
                                size: 16,
                                color: MetaTheme.coralAlert,
                              ),
                              onPressed: () => setState(() => _error = null),
                            ),
                          ],
                        ),
                      ),
                    ),

                  // Tab 0: Mission Control
                  if (_selectedNavIndex == 0) ...[
                    // Interactive Industry Solution Switcher
                    SolutionShowcaseBar(
                      selectedScenarioId: _selectedScenarioId,
                      onSelectScenario: _onSelectScenario,
                      running: _running,
                    ),
                    const SizedBox(height: 8),

                    // Two-Column Mission Control & Visual Grounding Radar
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      child: LayoutBuilder(
                        builder: (context, constraints) {
                          final isWide = constraints.maxWidth > 950;
                          final leftWidget = Column(
                            children: [
                              RunPanel(
                                workflows: _workflows,
                                selectedWorkflow: _workflow,
                                onSelectWorkflow: (v) {
                                  setState(() => _workflow = v);
                                  _refresh();
                                },
                                injectModal: _injectModal,
                                onInjectModal: (v) =>
                                    setState(() => _injectModal = v),
                                driver: _driver,
                                onSelectDriver: (d) {
                                  setState(() {
                                    _driver = d;
                                    if (d == 'adb' || d == 'desktop') {
                                      _workflow = 'w2';
                                    }
                                  });
                                },
                                intentController: _intentController,
                                running: _running,
                                onRun: _run,
                                spans: _spans,
                                trace: _trace,
                                baseUrl: _baseUrl,
                                adbAvailable: _health?.adbAvailable ?? false,
                                api: _api,
                              ),
                            ],
                          );

                          final rightWidget = SomViewer(
                            api: _api,
                            workflow: _workflow,
                            states: _states,
                            selectedState: _state,
                            onSelectState: (s) => setState(() => _state = s),
                            traceId: _trace?.traceId,
                            isRunning: _running,
                            driver: _driver,
                          );

                          if (isWide) {
                            return Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Expanded(flex: 5, child: leftWidget),
                                const SizedBox(width: 14),
                                Expanded(flex: 6, child: rightWidget),
                              ],
                            );
                          } else {
                            return Column(
                              children: [
                                leftWidget,
                                const SizedBox(height: 14),
                                rightWidget,
                              ],
                            );
                          }
                        },
                      ),
                    ),
                    const SizedBox(height: 14),

                    // Step plan graph (live records light up nodes during runs)
                    if (_trace?.plan.steps.isNotEmpty ?? false)
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        child: StepGraphView(
                          steps: _trace?.plan.steps ?? const [],
                          records: _running
                              ? _liveRecords
                              : (_trace?.records ?? const []),
                          planSummary: _trace?.plan.planSummary,
                          isRunning: _running,
                        ),
                      ),
                    if (_trace?.plan.steps.isNotEmpty ?? false)
                      const SizedBox(height: 12),

                    // Headline Performance & Telemetry KPI Row (Placed under Steps Execution)
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      child: MetricsRow(
                        trace: _trace,
                        liveRecords: _running ? _liveRecords : null,
                        dpiScale: _health?.displayDpiScale ?? 2.0,
                        verifierName:
                            _config?.verifierDisplayName ?? 'Verifier',
                      ),
                    ),
                    const SizedBox(height: 14),

                    // Audit Ledger
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      child: LedgerPanel(
                        records: _running
                            ? _liveRecords
                            : (_trace?.records ?? const []),
                        isLive: _running,
                      ),
                    ),
                  ],

                  // Tab 1: Device Fleet Manager
                  if (_selectedNavIndex == 1)
                    Padding(
                      padding: const EdgeInsets.all(16),
                      child: FleetManagerView(
                        selectedDriver: _driver,
                        onSelectDriver: (d) => setState(() => _driver = d),
                        adbAvailable: _health?.adbAvailable ?? false,
                        executionMode: _health?.executionMode ?? 'unknown',
                      ),
                    ),

                  // Tab 2: Developer Hub & SDK
                  if (_selectedNavIndex == 2)
                    Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        children: [
                          ConnectionBar(
                            baseUrl: _baseUrl,
                            health: _health,
                            config: _config,
                            refreshing: _refreshing,
                            onApply: _applyBaseUrl,
                            onRefresh: _refresh,
                          ),
                          const SizedBox(height: 16),
                          DeveloperHubView(baseUrl: _baseUrl),
                        ],
                      ),
                    ),

                  // Tab 3: Governance & Security
                  if (_selectedNavIndex == 3)
                    Padding(
                      padding: const EdgeInsets.all(16),
                      child: GovernanceView(
                        verifierLabel:
                            _config?.verifierDisplayName ?? 'Verifier',
                      ),
                    ),

                  // Tab 4: Rehearsal Benchmarks & History
                  if (_selectedNavIndex == 4)
                    Padding(
                      padding: const EdgeInsets.all(16),
                      child: LayoutBuilder(
                        builder: (context, constraints) {
                          final isWide = constraints.maxWidth > 950;
                          final benchWidget = BenchmarkPanel(
                            report: _benchmark,
                          );
                          final historyWidget = HistoryPanel(
                            history: _history,
                            activeTraceId: _trace?.traceId,
                            onSelect: _loadTrace,
                          );

                          if (isWide) {
                            return Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Expanded(flex: 6, child: benchWidget),
                                const SizedBox(width: 14),
                                Expanded(flex: 5, child: historyWidget),
                              ],
                            );
                          } else {
                            return Column(
                              children: [
                                benchWidget,
                                const SizedBox(height: 14),
                                historyWidget,
                              ],
                            );
                          }
                        },
                      ),
                    ),

                  const SizedBox(height: 24),
                ],
              ),
            ),
          ),

          // Slide-over Cloud Shell Terminal Drawer
          if (_showTerminal)
            TerminalDrawer(
              baseUrl: _baseUrl,
              onClose: () => setState(() => _showTerminal = false),
            ),
        ],
      ),
    ),
  ],
),
);
  }

  Widget _appBarBadge({
    required IconData icon,
    required String label,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: color),
          const SizedBox(width: 5),
          Text(
            label,
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w700,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}
