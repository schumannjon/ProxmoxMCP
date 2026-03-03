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
    assert "get_vm_config" in tool_names
    assert "get_vm_status" in tool_names
    assert "start_vm" in tool_names
    assert "stop_vm" in tool_names
    assert "shutdown_vm" in tool_names
    assert "reboot_vm" in tool_names
    assert "execute_vm_command" in tool_names
    assert "get_containers" in tool_names
    assert "get_container_config" in tool_names
    assert "get_container_status" in tool_names
    assert "start_container" in tool_names
    assert "stop_container" in tool_names
    assert "shutdown_container" in tool_names
    assert "reboot_container" in tool_names
    assert "clone_vm" in tool_names

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
        {"vmid": "101", "name": "vm2", "status": "stopped", "mem": 0, "maxmem": 0, "template": 1},
    ]
    mock_proxmox.return_value.nodes.return_value.qemu.return_value.config.get.return_value = {
        "cores": 2
    }

    response = await server.mcp.call_tool("get_vms", {})

    assert len(response) == 1
    text = response[0].text
    assert "vm1" in text
    assert "vm2" in text
    assert "Template" in text

@pytest.mark.asyncio
async def test_get_vm_config(server, mock_proxmox):
    """Test get_vm_config returns formatted config for a specific VM."""
    mock_proxmox.return_value.nodes.return_value.qemu.return_value.config.get.return_value = {
        "name": "ubuntu-server",
        "ostype": "l26",
        "cores": 4,
        "sockets": 1,
        "memory": 4096,
        "bios": "seabios",
        "machine": "pc-i440fx-8.1",
        "onboot": 1,
        "bootdisk": "scsi0",
        "scsi0": "local-lvm:vm-100-disk-0,size=32G",
        "net0": "virtio=BC:24:11:AA:BB:CC,bridge=vmbr0",
        "agent": "enabled=1",
    }

    response = await server.mcp.call_tool("get_vm_config", {"node": "node1", "vmid": "100"})

    assert len(response) == 1
    text = response[0].text
    assert "ubuntu-server" in text
    assert "l26" in text
    assert "scsi0" in text
    assert "vmbr0" in text

@pytest.mark.asyncio
async def test_get_vm_config_missing_parameters(server):
    """Test get_vm_config with missing parameters."""
    with pytest.raises(ToolError, match="Field required"):
        await server.mcp.call_tool("get_vm_config", {})

@pytest.mark.asyncio
async def test_get_vm_status(server, mock_proxmox):
    """Test get_vm_status tool returns formatted text with VM status info."""
    mock_proxmox.return_value.nodes.return_value.qemu.return_value.status.current.get.return_value = {
        "status": "running",
        "name": "vm1",
        "uptime": 3600,
        "cpus": 4,
        "cpu": 0.10,
        "mem": 2147483648,
        "maxmem": 8589934592,
        "disk": 10737418240,
        "maxdisk": 53687091200,
    }

    response = await server.mcp.call_tool("get_vm_status", {"node": "node1", "vmid": "100"})

    assert len(response) == 1
    text = response[0].text
    assert "vm1" in text
    assert "RUNNING" in text

@pytest.mark.asyncio
async def test_get_vm_status_missing_parameters(server):
    """Test get_vm_status with missing parameters."""
    with pytest.raises(ToolError, match="Field required"):
        await server.mcp.call_tool("get_vm_status", {})

@pytest.mark.asyncio
async def test_start_vm(server, mock_proxmox):
    """Test start_vm returns a task ID."""
    mock_proxmox.return_value.nodes.return_value.qemu.return_value.status.start.post.return_value = (
        "UPID:node1:00001234:00000001:5E3F4A2B:qmstart:100:root@pam:"
    )

    response = await server.mcp.call_tool("start_vm", {"node": "node1", "vmid": "100"})

    assert len(response) == 1
    assert "start" in response[0].text
    assert "100" in response[0].text

@pytest.mark.asyncio
async def test_stop_vm(server, mock_proxmox):
    """Test stop_vm returns a task ID."""
    mock_proxmox.return_value.nodes.return_value.qemu.return_value.status.stop.post.return_value = (
        "UPID:node1:00001234:00000001:5E3F4A2B:qmstop:100:root@pam:"
    )

    response = await server.mcp.call_tool("stop_vm", {"node": "node1", "vmid": "100"})

    assert len(response) == 1
    assert "stop" in response[0].text

@pytest.mark.asyncio
async def test_shutdown_vm(server, mock_proxmox):
    """Test shutdown_vm returns a task ID."""
    mock_proxmox.return_value.nodes.return_value.qemu.return_value.status.shutdown.post.return_value = (
        "UPID:node1:00001234:00000001:5E3F4A2B:qmshutdown:100:root@pam:"
    )

    response = await server.mcp.call_tool("shutdown_vm", {"node": "node1", "vmid": "100"})

    assert len(response) == 1
    assert "shutdown" in response[0].text

@pytest.mark.asyncio
async def test_reboot_vm(server, mock_proxmox):
    """Test reboot_vm returns a task ID."""
    mock_proxmox.return_value.nodes.return_value.qemu.return_value.status.reboot.post.return_value = (
        "UPID:node1:00001234:00000001:5E3F4A2B:qmreboot:100:root@pam:"
    )

    response = await server.mcp.call_tool("reboot_vm", {"node": "node1", "vmid": "100"})

    assert len(response) == 1
    assert "reboot" in response[0].text

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
async def test_get_containers(server, mock_proxmox):
    """Test get_containers tool returns formatted text containing container names."""
    mock_proxmox.return_value.nodes.get.return_value = [
        {"node": "node1", "status": "online"}
    ]
    mock_proxmox.return_value.nodes.return_value.lxc.get.return_value = [
        {"vmid": "200", "name": "ct1", "status": "running", "mem": 0, "maxmem": 0},
        {"vmid": "201", "name": "ct2", "status": "stopped", "mem": 0, "maxmem": 0},
    ]
    mock_proxmox.return_value.nodes.return_value.lxc.return_value.config.get.return_value = {
        "cores": 2
    }

    response = await server.mcp.call_tool("get_containers", {})

    assert len(response) == 1
    text = response[0].text
    assert "ct1" in text
    assert "ct2" in text

@pytest.mark.asyncio
async def test_get_containers_empty(server, mock_proxmox):
    """Test get_containers tool with no containers returns a no-containers message."""
    mock_proxmox.return_value.nodes.get.return_value = [
        {"node": "node1", "status": "online"}
    ]
    mock_proxmox.return_value.nodes.return_value.lxc.get.return_value = []

    response = await server.mcp.call_tool("get_containers", {})

    assert len(response) == 1
    assert "No containers" in response[0].text

@pytest.mark.asyncio
async def test_get_container_config(server, mock_proxmox):
    """Test get_container_config returns formatted config for a specific container."""
    mock_proxmox.return_value.nodes.return_value.lxc.return_value.config.get.return_value = {
        "hostname": "nginx-proxy",
        "ostype": "debian",
        "cores": 2,
        "memory": 1024,
        "swap": 512,
        "unprivileged": 1,
        "onboot": 1,
        "rootfs": "local-lvm:vm-200-disk-0,size=4G",
        "net0": "name=eth0,bridge=vmbr0,ip=192.168.1.100/24,gw=192.168.1.1,type=veth",
        "features": "nesting=1",
    }

    response = await server.mcp.call_tool("get_container_config", {"node": "node1", "vmid": "200"})

    assert len(response) == 1
    text = response[0].text
    assert "nginx-proxy" in text
    assert "debian" in text
    assert "eth0" in text
    assert "192.168.1.100/24" in text

@pytest.mark.asyncio
async def test_get_container_config_missing_parameters(server):
    """Test get_container_config with missing parameters."""
    with pytest.raises(ToolError, match="Field required"):
        await server.mcp.call_tool("get_container_config", {})

@pytest.mark.asyncio
async def test_get_container_status(server, mock_proxmox):
    """Test get_container_status returns formatted status for a specific container."""
    mock_proxmox.return_value.nodes.return_value.lxc.return_value.status.current.get.return_value = {
        "status": "running",
        "name": "ct1",
        "uptime": 3600,
        "cpus": 2,
        "cpu": 0.05,
        "mem": 134217728,
        "maxmem": 536870912,
        "disk": 1073741824,
        "maxdisk": 10737418240,
    }

    response = await server.mcp.call_tool("get_container_status", {"node": "node1", "vmid": "200"})

    assert len(response) == 1
    text = response[0].text
    assert "ct1" in text
    assert "RUNNING" in text

@pytest.mark.asyncio
async def test_get_container_status_missing_parameters(server):
    """Test get_container_status with missing parameters."""
    with pytest.raises(ToolError, match="Field required"):
        await server.mcp.call_tool("get_container_status", {})

@pytest.mark.asyncio
async def test_start_container(server, mock_proxmox):
    """Test start_container returns a task ID."""
    mock_proxmox.return_value.nodes.return_value.lxc.return_value.status.start.post.return_value = (
        "UPID:node1:00001234:00000001:5E3F4A2B:vzstart:200:root@pam:"
    )

    response = await server.mcp.call_tool("start_container", {"node": "node1", "vmid": "200"})

    assert len(response) == 1
    assert "start" in response[0].text
    assert "200" in response[0].text

@pytest.mark.asyncio
async def test_stop_container(server, mock_proxmox):
    """Test stop_container returns a task ID."""
    mock_proxmox.return_value.nodes.return_value.lxc.return_value.status.stop.post.return_value = (
        "UPID:node1:00001234:00000001:5E3F4A2B:vzstop:200:root@pam:"
    )

    response = await server.mcp.call_tool("stop_container", {"node": "node1", "vmid": "200"})

    assert len(response) == 1
    assert "stop" in response[0].text

@pytest.mark.asyncio
async def test_shutdown_container(server, mock_proxmox):
    """Test shutdown_container returns a task ID."""
    mock_proxmox.return_value.nodes.return_value.lxc.return_value.status.shutdown.post.return_value = (
        "UPID:node1:00001234:00000001:5E3F4A2B:vzshutdown:200:root@pam:"
    )

    response = await server.mcp.call_tool("shutdown_container", {"node": "node1", "vmid": "200"})

    assert len(response) == 1
    assert "shutdown" in response[0].text

@pytest.mark.asyncio
async def test_reboot_container(server, mock_proxmox):
    """Test reboot_container returns a task ID."""
    mock_proxmox.return_value.nodes.return_value.lxc.return_value.status.reboot.post.return_value = (
        "UPID:node1:00001234:00000001:5E3F4A2B:vzreboot:200:root@pam:"
    )

    response = await server.mcp.call_tool("reboot_container", {"node": "node1", "vmid": "200"})

    assert len(response) == 1
    assert "reboot" in response[0].text

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

@pytest.mark.asyncio
async def test_clone_vm(server, mock_proxmox):
    """Test clone_vm returns new VM ID and task ID."""
    mock_proxmox.return_value.nodes.return_value.qemu.return_value.clone.post.return_value = (
        "UPID:node1:00001234:00000001:5E3F4A2B:qmclone:100:root@pam:"
    )

    response = await server.mcp.call_tool("clone_vm", {
        "node": "node1",
        "vmid": "100",
        "newid": "200",
    })

    assert len(response) == 1
    text = response[0].text
    assert "200" in text
    assert "UPID" in text

@pytest.mark.asyncio
async def test_clone_vm_missing_parameters(server):
    """Test clone_vm with missing required parameters raises ToolError."""
    with pytest.raises(ToolError, match="Field required"):
        await server.mcp.call_tool("clone_vm", {})
