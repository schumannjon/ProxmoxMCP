"""
Main server implementation for Proxmox MCP.

This module implements the core MCP server for Proxmox integration, providing:
- Configuration loading and validation
- Logging setup
- Proxmox API connection management
- MCP tool registration and routing
- Signal handling for graceful shutdown

The server exposes a set of tools for managing Proxmox resources including:
- Node management
- VM operations
- Storage management
- Cluster status monitoring
"""
import logging
import os
import sys
import signal
from typing import Optional, List, Annotated

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.tools import Tool
from mcp.types import TextContent as Content
from pydantic import Field

from .config.loader import load_config
from .core.logging import setup_logging
from .core.proxmox import ProxmoxManager
from .tools.node import NodeTools
from .tools.vm import VMTools
from .tools.storage import StorageTools
from .tools.cluster import ClusterTools
from .tools.lxc import LXCTools
from .tools.definitions import (
    GET_NODES_DESC,
    GET_NODE_STATUS_DESC,
    GET_VMS_DESC,
    GET_VM_CONFIG_DESC,
    GET_VM_STATUS_DESC,
    EXECUTE_VM_COMMAND_DESC,
    START_VM_DESC,
    STOP_VM_DESC,
    SHUTDOWN_VM_DESC,
    REBOOT_VM_DESC,
    CLONE_VM_DESC,
    GET_CONTAINERS_DESC,
    GET_CONTAINER_CONFIG_DESC,
    GET_CONTAINER_STATUS_DESC,
    START_CONTAINER_DESC,
    STOP_CONTAINER_DESC,
    SHUTDOWN_CONTAINER_DESC,
    REBOOT_CONTAINER_DESC,
    GET_STORAGE_DESC,
    GET_CLUSTER_STATUS_DESC,
)

class ProxmoxMCPServer:
    """Main server class for Proxmox MCP."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the server.

        Args:
            config_path: Path to configuration file
        """
        self.config = load_config(config_path)
        self.logger = setup_logging(self.config.logging)
        
        # Initialize core components
        self.proxmox_manager = ProxmoxManager(self.config.proxmox, self.config.auth)
        self.proxmox = self.proxmox_manager.get_api()
        
        # Initialize tools
        self.node_tools = NodeTools(self.proxmox)
        self.vm_tools = VMTools(self.proxmox)
        self.storage_tools = StorageTools(self.proxmox)
        self.cluster_tools = ClusterTools(self.proxmox)
        self.lxc_tools = LXCTools(self.proxmox)
        
        # Initialize MCP server
        self.mcp = FastMCP("ProxmoxMCP")
        self._setup_tools()

    def _setup_tools(self) -> None:
        """Register MCP tools with the server.
        
        Initializes and registers all available tools with the MCP server:
        - Node management tools (list nodes, get status)
        - VM operation tools (list VMs, execute commands)
        - Storage management tools (list storage)
        - Cluster tools (get cluster status)
        
        Each tool is registered with appropriate descriptions and parameter
        validation using Pydantic models.
        """
        
        # Node tools
        @self.mcp.tool(description=GET_NODES_DESC)
        def get_nodes():
            return self.node_tools.get_nodes()

        @self.mcp.tool(description=GET_NODE_STATUS_DESC)
        def get_node_status(
            node: Annotated[str, Field(description="Name/ID of node to query (e.g. 'pve1', 'proxmox-node2')")]
        ):
            return self.node_tools.get_node_status(node)

        # VM tools
        @self.mcp.tool(description=GET_VMS_DESC)
        def get_vms():
            return self.vm_tools.get_vms()

        @self.mcp.tool(description=GET_VM_CONFIG_DESC)
        def get_vm_config(
            node: Annotated[str, Field(description="Host node name (e.g. 'pve1')")],
            vmid: Annotated[str, Field(description="VM ID number (e.g. '100')")],
        ):
            return self.vm_tools.get_vm_config(node, vmid)

        @self.mcp.tool(description=GET_VM_STATUS_DESC)
        def get_vm_status(
            node: Annotated[str, Field(description="Host node name (e.g. 'pve1')")],
            vmid: Annotated[str, Field(description="VM ID number (e.g. '100')")],
        ):
            return self.vm_tools.get_vm_status(node, vmid)

        @self.mcp.tool(description=START_VM_DESC)
        def start_vm(
            node: Annotated[str, Field(description="Host node name (e.g. 'pve1')")],
            vmid: Annotated[str, Field(description="VM ID number (e.g. '100')")],
        ):
            return self.vm_tools.start_vm(node, vmid)

        @self.mcp.tool(description=STOP_VM_DESC)
        def stop_vm(
            node: Annotated[str, Field(description="Host node name (e.g. 'pve1')")],
            vmid: Annotated[str, Field(description="VM ID number (e.g. '100')")],
        ):
            return self.vm_tools.stop_vm(node, vmid)

        @self.mcp.tool(description=SHUTDOWN_VM_DESC)
        def shutdown_vm(
            node: Annotated[str, Field(description="Host node name (e.g. 'pve1')")],
            vmid: Annotated[str, Field(description="VM ID number (e.g. '100')")],
        ):
            return self.vm_tools.shutdown_vm(node, vmid)

        @self.mcp.tool(description=REBOOT_VM_DESC)
        def reboot_vm(
            node: Annotated[str, Field(description="Host node name (e.g. 'pve1')")],
            vmid: Annotated[str, Field(description="VM ID number (e.g. '100')")],
        ):
            return self.vm_tools.reboot_vm(node, vmid)

        @self.mcp.tool(description=CLONE_VM_DESC)
        def clone_vm(
            node: Annotated[str, Field(description="Host node name (e.g. 'pve1')")],
            vmid: Annotated[str, Field(description="Source VM/template ID (e.g. '100')")],
            newid: Annotated[str, Field(description="New VM ID for the clone (e.g. '200')")],
            name: Annotated[Optional[str], Field(description="Name for the new VM")] = None,
            target: Annotated[Optional[str], Field(description="Target node for the clone")] = None,
            full: Annotated[bool, Field(description="Full clone (true) or linked clone (false)")] = True,
        ):
            return self.vm_tools.clone_vm(node, vmid, newid, name, target, full)

        @self.mcp.tool(description=EXECUTE_VM_COMMAND_DESC)
        async def execute_vm_command(
            node: Annotated[str, Field(description="Host node name (e.g. 'pve1', 'proxmox-node2')")],
            vmid: Annotated[str, Field(description="VM ID number (e.g. '100', '101')")],
            command: Annotated[str, Field(description="Shell command to run (e.g. 'uname -a', 'systemctl status nginx')")]
        ):
            return await self.vm_tools.execute_command(node, vmid, command)

        # LXC tools
        @self.mcp.tool(description=GET_CONTAINERS_DESC)
        def get_containers():
            return self.lxc_tools.get_containers()

        @self.mcp.tool(description=GET_CONTAINER_CONFIG_DESC)
        def get_container_config(
            node: Annotated[str, Field(description="Host node name (e.g. 'pve1')")],
            vmid: Annotated[str, Field(description="Container ID number (e.g. '200')")],
        ):
            return self.lxc_tools.get_container_config(node, vmid)

        @self.mcp.tool(description=GET_CONTAINER_STATUS_DESC)
        def get_container_status(
            node: Annotated[str, Field(description="Host node name (e.g. 'pve1')")],
            vmid: Annotated[str, Field(description="Container ID number (e.g. '200')")],
        ):
            return self.lxc_tools.get_container_status(node, vmid)

        @self.mcp.tool(description=START_CONTAINER_DESC)
        def start_container(
            node: Annotated[str, Field(description="Host node name (e.g. 'pve1')")],
            vmid: Annotated[str, Field(description="Container ID number (e.g. '200')")],
        ):
            return self.lxc_tools.start_container(node, vmid)

        @self.mcp.tool(description=STOP_CONTAINER_DESC)
        def stop_container(
            node: Annotated[str, Field(description="Host node name (e.g. 'pve1')")],
            vmid: Annotated[str, Field(description="Container ID number (e.g. '200')")],
        ):
            return self.lxc_tools.stop_container(node, vmid)

        @self.mcp.tool(description=SHUTDOWN_CONTAINER_DESC)
        def shutdown_container(
            node: Annotated[str, Field(description="Host node name (e.g. 'pve1')")],
            vmid: Annotated[str, Field(description="Container ID number (e.g. '200')")],
        ):
            return self.lxc_tools.shutdown_container(node, vmid)

        @self.mcp.tool(description=REBOOT_CONTAINER_DESC)
        def reboot_container(
            node: Annotated[str, Field(description="Host node name (e.g. 'pve1')")],
            vmid: Annotated[str, Field(description="Container ID number (e.g. '200')")],
        ):
            return self.lxc_tools.reboot_container(node, vmid)

        # Storage tools
        @self.mcp.tool(description=GET_STORAGE_DESC)
        def get_storage():
            return self.storage_tools.get_storage()

        # Cluster tools
        @self.mcp.tool(description=GET_CLUSTER_STATUS_DESC)
        def get_cluster_status():
            return self.cluster_tools.get_cluster_status()

    def start(self) -> None:
        """Start the MCP server.
        
        Initializes the server with:
        - Signal handlers for graceful shutdown (SIGINT, SIGTERM)
        - Async runtime for handling concurrent requests
        - Error handling and logging
        
        The server runs until terminated by a signal or fatal error.
        """
        import anyio

        def signal_handler(signum, frame):
            self.logger.info("Received signal to shutdown...")
            sys.exit(0)

        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            self.logger.info("Starting MCP server...")
            anyio.run(self.mcp.run_stdio_async)
        except Exception as e:
            self.logger.error(f"Server error: {e}")
            sys.exit(1)

def main() -> None:
    """Entry point for the proxmox-mcp console script."""
    config_path = os.getenv("PROXMOX_MCP_CONFIG")
    try:
        server = ProxmoxMCPServer(config_path)
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
