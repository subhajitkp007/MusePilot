# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Test suite for the MusePilot Model Context Protocol (MCP) server."""

from __future__ import annotations

import json

import pytest

from musepilot.mcp.server import create_mcp_server


@pytest.fixture
def mcp_server():
    """Instantiate a fresh MusePilot MCP server for testing."""
    return create_mcp_server()


@pytest.mark.anyio
async def test_mcp_tools_registration(mcp_server):
    """Verify that all core MusePilot capability tools are registered."""
    tools = await mcp_server.list_tools()
    tool_names = {t.name for t in tools}

    expected_tools = {
        "musepilot_health",
        "musepilot_list_workflows",
        "musepilot_execute_workflow",
        "musepilot_list_traces",
        "musepilot_get_trace",
        "musepilot_get_benchmarks",
        "musepilot_list_devices",
        "musepilot_transcribe_voice",
    }
    assert expected_tools.issubset(tool_names), f"Missing tools: {expected_tools - tool_names}"


@pytest.mark.anyio
async def test_mcp_resources_registration(mcp_server):
    """Verify that standard URIs are exposed as MCP resources."""
    resources = await mcp_server.list_resources()
    resource_uris = {str(r.uri) for r in resources}

    expected_uris = {
        "musepilot://health",
        "musepilot://workflows",
        "musepilot://benchmarks",
        "musepilot://traces/latest",
        "musepilot://devices",
    }
    assert expected_uris.issubset(resource_uris), f"Missing URIs: {expected_uris - resource_uris}"


@pytest.mark.anyio
async def test_mcp_prompts_registration(mcp_server):
    """Verify prompt templates are registered for autonomous agent execution."""
    prompts = await mcp_server.list_prompts()
    prompt_names = {p.name for p in prompts}

    assert "visual_regression_audit" in prompt_names
    assert "self_healing_recovery_test" in prompt_names


@pytest.mark.anyio
async def test_mcp_tool_health_execution(mcp_server):
    """Verify musepilot_health tool executes cleanly and returns readiness info."""
    result = await mcp_server.call_tool("musepilot_health", {})
    assert not result.is_error
    assert len(result.content) > 0

    payload = json.loads(result.content[0].text)
    assert "passed" in payload
    assert "sam_model_id" in payload
    assert "planner_model_id" in payload
    assert "execution_mode" in payload


@pytest.mark.anyio
async def test_mcp_tool_list_workflows(mcp_server):
    """Verify musepilot_list_workflows tool returns frozen W1 and W2 workflows."""
    result = await mcp_server.call_tool("musepilot_list_workflows", {})
    assert not result.is_error

    payload = json.loads(result.content[0].text)
    assert "workflows" in payload
    workflows = payload["workflows"]
    assert len(workflows) == 2
    workflow_ids = [w["workflow_id"] for w in workflows]
    assert "w1" in workflow_ids
    assert "w2" in workflow_ids


@pytest.mark.anyio
async def test_mcp_tool_list_devices(mcp_server):
    """Verify musepilot_list_devices tool discovers ADB and display info."""
    result = await mcp_server.call_tool("musepilot_list_devices", {})
    assert not result.is_error

    devices_info = json.loads(result.content[0].text)
    assert "adb_available" in devices_info
    assert "adb_devices" in devices_info
    assert isinstance(devices_info["adb_devices"], list)
    assert "display_dpi_scale" in devices_info


@pytest.mark.anyio
async def test_mcp_tool_get_benchmarks(mcp_server):
    """Verify musepilot_get_benchmarks calculates quantitative reliability metrics."""
    result = await mcp_server.call_tool("musepilot_get_benchmarks", {})
    assert not result.is_error

    bench = json.loads(result.content[0].text)
    assert "total_runs_analyzed" in bench
    assert "mean_mask_hit_rate" in bench
    assert "mean_verification_pass_rate" in bench


@pytest.mark.anyio
async def test_mcp_tool_execute_workflow_simulated(mcp_server):
    """Verify musepilot_execute_workflow executes closed-loop W1 run."""
    result = await mcp_server.call_tool(
        "musepilot_execute_workflow",
        {"workflow_id": "w1", "driver": "simulated"},
    )
    assert not result.is_error

    trace = json.loads(result.content[0].text)
    assert trace["workflow_id"] == "w1"
    assert "records" in trace
    assert len(trace["records"]) > 0
    assert trace["metrics"]["mask_centroid_hit_rate"] == 1.0


@pytest.mark.anyio
async def test_mcp_tool_list_and_get_traces(mcp_server):
    """Verify listing and retrieving traces through MCP tools."""
    # List traces
    list_res = await mcp_server.call_tool("musepilot_list_traces", {"limit": 5})
    assert not list_res.is_error
    payload = json.loads(list_res.content[0].text)
    assert "traces" in payload
    assert isinstance(payload["traces"], list)

    # Get latest trace
    latest_res = await mcp_server.call_tool(
        "musepilot_get_trace", {"trace_id": "latest", "workflow_id": "w1"}
    )
    assert not latest_res.is_error
    latest_trace = json.loads(latest_res.content[0].text)
    assert "workflow_id" in latest_trace
    assert latest_trace["workflow_id"] == "w1"


@pytest.mark.anyio
async def test_mcp_resource_read(mcp_server):
    """Verify reading MCP resources returns valid JSON."""
    health_content = await mcp_server.read_resource("musepilot://health")
    assert len(health_content) > 0
    health_json = json.loads(health_content[0].content)
    assert "passed" in health_json

    bench_content = await mcp_server.read_resource("musepilot://benchmarks")
    assert len(bench_content) > 0
    bench_json = json.loads(bench_content[0].content)
    assert "total_runs_analyzed" in bench_json


@pytest.mark.anyio
async def test_mcp_prompt_get(mcp_server):
    """Verify retrieving prompt templates."""
    prompt = await mcp_server.get_prompt(
        "visual_regression_audit", {"workflow_id": "w1", "driver": "adb"}
    )
    assert len(prompt.messages) > 0
    msg_text = prompt.messages[0].content.text
    assert "visual regression" in msg_text.lower()
    assert "w1" in msg_text
    assert "adb" in msg_text
