"""
Tests for the Proxmox MCP server.
"""

import os
import pytest
from unittest.mock import Mock, patch

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from proxmox_mcp.server import ProxmoxMCPServer

@pytest.fixture
def mock_env_vars():
    """Fixture to set up test environment variables."""
    env_vars = {
        "PROXMOX_HOST": "test.proxmox.com",
        "PROXMOX_USER": "test@pve",
        "PROXMOX_TOKEN_NAME": "test_token",
        "PROXMOX_TOKEN_VALUE": "test_value",
        "LOG_LEVEL": "DEBUG"
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars

@pytest.fixture
def mock_proxmox():
    """Fixture to mock ProxmoxAPI."""
    with patch("proxmox_mcp.core.proxmox.ProxmoxAPI") as mock:
        mock.return_value.nodes.get.return_value = [
            {"node": "node1", "status": "online"},
            {"node": "node2", "status": "online"}
        ]
        # Default per-node status (used by get_nodes and get_node_status)
        mock.return_value.nodes.return_value.status.get.return_value = {
            "status": "online",
            "uptime": 12345,
            "maxcpu": 4,
            "memory": {"used": 1073741824, "total": 4294967296},
        }
        yield mock

@pytest.fixture
def server(mock_env_vars, mock_proxmox):
    """Fixture to create a ProxmoxMCPServer instance."""
    return ProxmoxMCPServer()

def test_server_initialization(server, mock_proxmox):
    """Test server initialization with environment variables."""
    assert server.config.proxmox.host == "test.proxmox.com"
    assert server.config.auth.user == "test@pve"
    assert server.config.auth.token_name == "test_token"
    assert server.config.auth.token_value == "test_value"
    assert server.config.logging.level == "DEBUG"

    mock_proxmox.assert_called_once()

@pytest.mark.asyncio
async def test_list_tools(server):
    """Test listing available tools."""
    tools = await server.mcp.list_tools()

    assert len(tools) > 0
    tool_names = [tool.name for tool in tools]
    assert "get_nodes" in tool_names
    assert "get_vms" in tool_names
    assert "execute_vm_command" in tool_names
    # get_containers is intentionally not registered (see CLAUDE.md)
    assert "get_containers" not in tool_names

@pytest.mark.asyncio
async def test_get_nodes(server, mock_proxmox):
    """Test get_nodes tool returns formatted text containing node names."""
    mock_proxmox.return_value.nodes.get.return_value = [
        {"node": "node1", "status": "online"},
        {"node": "node2", "status": "online"}
    ]
    mock_proxmox.return_value.nodes.return_value.status.get.return_value = {
        "uptime": 12345,
        "maxcpu": 4,
        "memory": {"used": 1073741824, "total": 4294967296},
    }

    response = await server.mcp.call_tool("get_nodes", {})

    assert len(response) == 1
    text = response[0].text
    assert "node1" in text
    assert "node2" in text

@pytest.mark.asyncio
async def test_get_node_status_missing_parameter(server):
    """Test get_node_status tool with missing parameter."""
    with pytest.raises(ToolError, match="Field required"):
        await server.mcp.call_tool("get_node_status", {})

@pytest.mark.asyncio
async def test_get_node_status(server, mock_proxmox):
    """Test get_node_status tool returns formatted text with status info."""
    mock_proxmox.return_value.nodes.return_value.status.get.return_value = {
        "status": "running",
        "uptime": 123456,
        "maxcpu": 4,
        "memory": {"used": 1073741824, "total": 4294967296},
    }

    response = await server.mcp.call_tool("get_node_status", {"node": "node1"})

    assert len(response) == 1
    text = response[0].text
    assert "node1" in text
    assert "RUNNING" in text

@pytest.mark.asyncio
async def test_get_vms(server, mock_proxmox):
    """Test get_vms tool returns formatted text containing VM names."""
    mock_proxmox.return_value.nodes.get.return_value = [
        {"node": "node1", "status": "online"}
    ]
    mock_proxmox.return_value.nodes.return_value.qemu.get.return_value = [
        {"vmid": "100", "name": "vm1", "status": "running", "mem": 0, "maxmem": 0},
        {"vmid": "101", "name": "vm2", "status": "stopped", "mem": 0, "maxmem": 0}
    ]
    mock_proxmox.return_value.nodes.return_value.qemu.return_value.config.get.return_value = {
        "cores": 2
    }

    response = await server.mcp.call_tool("get_vms", {})

    assert len(response) == 1
    text = response[0].text
    assert "vm1" in text
    assert "vm2" in text

@pytest.mark.asyncio
async def test_get_storage(server, mock_proxmox):
    """Test get_storage tool returns formatted text containing storage pool names."""
    mock_proxmox.return_value.storage.get.return_value = [
        {"storage": "local", "type": "dir"},
        {"storage": "ceph", "type": "rbd"}
    ]
    mock_proxmox.return_value.nodes.return_value.storage.return_value.status.get.return_value = {
        "used": 10737418240,
        "total": 107374182400,
        "avail": 96636764160,
    }

    response = await server.mcp.call_tool("get_storage", {})

    assert len(response) == 1
    text = response[0].text
    assert "local" in text
    assert "ceph" in text

@pytest.mark.asyncio
async def test_get_cluster_status(server, mock_proxmox):
    """Test get_cluster_status tool returns formatted text with cluster info."""
    mock_proxmox.return_value.cluster.status.get.return_value = [
        {"type": "cluster", "name": "proxmox-cluster", "quorate": 1, "nodes": 2},
        {"type": "node", "name": "node1", "online": 1, "local": 1},
        {"type": "node", "name": "node2", "online": 1, "local": 0},
    ]

    response = await server.mcp.call_tool("get_cluster_status", {})

    assert len(response) == 1
    assert response[0].text  # non-empty

@pytest.mark.asyncio
async def test_execute_vm_command_success(server, mock_proxmox):
    """Test successful VM command execution returns formatted output."""
    mock_proxmox.return_value.nodes.return_value.qemu.return_value.status.current.get.return_value = {
        "status": "running"
    }
    # endpoint("exec").post() and endpoint("exec-status").get() both go through
    # agent.return_value since MagicMock.__call__ always returns return_value
    mock_proxmox.return_value.nodes.return_value.qemu.return_value.agent.return_value.post.return_value = {
        "pid": 123
    }
    mock_proxmox.return_value.nodes.return_value.qemu.return_value.agent.return_value.get.return_value = {
        "out-data": "command output",
        "err-data": "",
        "exitcode": 0,
        "exited": 1,
    }

    response = await server.mcp.call_tool("execute_vm_command", {
        "node": "node1",
        "vmid": "100",
        "command": "ls -l"
    })

    assert len(response) == 1
    assert "command output" in response[0].text

@pytest.mark.asyncio
async def test_execute_vm_command_missing_parameters(server):
    """Test VM command execution with missing parameters."""
    with pytest.raises(ToolError):
        await server.mcp.call_tool("execute_vm_command", {})

@pytest.mark.asyncio
async def test_execute_vm_command_vm_not_running(server, mock_proxmox):
    """Test VM command execution when VM is not running."""
    mock_proxmox.return_value.nodes.return_value.qemu.return_value.status.current.get.return_value = {
        "status": "stopped"
    }

    with pytest.raises(ToolError, match="not running"):
        await server.mcp.call_tool("execute_vm_command", {
            "node": "node1",
            "vmid": "100",
            "command": "ls -l"
        })

@pytest.mark.asyncio
async def test_execute_vm_command_with_error(server, mock_proxmox):
    """Test VM command execution where the command returns a non-zero exit code."""
    mock_proxmox.return_value.nodes.return_value.qemu.return_value.status.current.get.return_value = {
        "status": "running"
    }
    mock_proxmox.return_value.nodes.return_value.qemu.return_value.agent.return_value.post.return_value = {
        "pid": 456
    }
    mock_proxmox.return_value.nodes.return_value.qemu.return_value.agent.return_value.get.return_value = {
        "out-data": "",
        "err-data": "command not found",
        "exitcode": 1,
        "exited": 1,
    }

    response = await server.mcp.call_tool("execute_vm_command", {
        "node": "node1",
        "vmid": "100",
        "command": "invalid-command"
    })

    assert len(response) == 1
    assert "command not found" in response[0].text
