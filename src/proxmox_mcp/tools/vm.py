"""
VM-related tools for Proxmox MCP.

This module provides tools for managing and interacting with Proxmox VMs:
- Listing all VMs across the cluster with their status
- Retrieving detailed VM information including:
  * Resource allocation (CPU, memory)
  * Runtime status
  * Node placement
- Executing commands within VMs via QEMU guest agent
- Handling VM console operations

The tools implement fallback mechanisms for scenarios where
detailed VM information might be temporarily unavailable.
"""
from typing import List, Optional
from mcp.types import TextContent as Content
from .base import ProxmoxTool
from .definitions import (
    GET_VMS_DESC,
    GET_VM_CONFIG_DESC,
    GET_VM_STATUS_DESC,
    EXECUTE_VM_COMMAND_DESC,
    START_VM_DESC,
    STOP_VM_DESC,
    SHUTDOWN_VM_DESC,
    REBOOT_VM_DESC,
    CLONE_VM_DESC,
)
from .console.manager import VMConsoleManager

class VMTools(ProxmoxTool):
    """Tools for managing Proxmox VMs.
    
    Provides functionality for:
    - Retrieving cluster-wide VM information
    - Getting detailed VM status and configuration
    - Executing commands within VMs
    - Managing VM console operations
    
    Implements fallback mechanisms for scenarios where detailed
    VM information might be temporarily unavailable. Integrates
    with QEMU guest agent for VM command execution.
    """

    def __init__(self, proxmox_api):
        """Initialize VM tools.

        Args:
            proxmox_api: Initialized ProxmoxAPI instance
        """
        super().__init__(proxmox_api)
        self.console_manager = VMConsoleManager(proxmox_api)

    def get_vms(self) -> List[Content]:
        """List all virtual machines across the cluster with detailed status.

        Retrieves comprehensive information for each VM including:
        - Basic identification (ID, name)
        - Runtime status (running, stopped)
        - Resource allocation and usage:
          * CPU cores
          * Memory allocation and usage
        - Node placement
        
        Implements a fallback mechanism that returns basic information
        if detailed configuration retrieval fails for any VM.

        Returns:
            List of Content objects containing formatted VM information:
            {
                "vmid": "100",
                "name": "vm-name",
                "status": "running/stopped",
                "node": "node-name",
                "cpus": core_count,
                "memory": {
                    "used": bytes,
                    "total": bytes
                }
            }

        Raises:
            RuntimeError: If the cluster-wide VM query fails
        """
        try:
            result = []
            for node in self.proxmox.nodes.get():
                node_name = node["node"]
                vms = self.proxmox.nodes(node_name).qemu.get()
                for vm in vms:
                    vmid = vm["vmid"]
                    # Get VM config for CPU cores
                    try:
                        config = self.proxmox.nodes(node_name).qemu(vmid).config.get()
                        entry = {
                            "vmid": vmid,
                            "name": vm["name"],
                            "status": vm["status"],
                            "node": node_name,
                            "cpus": config.get("cores", "N/A"),
                            "memory": {
                                "used": vm.get("mem", 0),
                                "total": vm.get("maxmem", 0)
                            }
                        }
                        if vm.get("template"):
                            entry["template"] = vm["template"]
                        result.append(entry)
                    except Exception:
                        # Fallback if can't get config
                        entry = {
                            "vmid": vmid,
                            "name": vm["name"],
                            "status": vm["status"],
                            "node": node_name,
                            "cpus": "N/A",
                            "memory": {
                                "used": vm.get("mem", 0),
                                "total": vm.get("maxmem", 0)
                            }
                        }
                        if vm.get("template"):
                            entry["template"] = vm["template"]
                        result.append(entry)
            return self._format_response(result, "vms")
        except Exception as e:
            self._handle_error("get VMs", e)

    def get_vm_config(self, node: str, vmid: str) -> List[Content]:
        """Get the configuration for a specific VM.

        Args:
            node: Host node name (e.g. 'pve1')
            vmid: VM ID (e.g. '100')

        Returns:
            List of Content objects with formatted VM config.

        Raises:
            ValueError: If the VM is not found
            RuntimeError: If config retrieval fails
        """
        try:
            config = self.proxmox.nodes(node).qemu(vmid).config.get()
            return self._format_response((vmid, config), "vm_config")
        except Exception as e:
            self._handle_error(f"get config for VM {vmid}", e)

    def get_vm_status(self, node: str, vmid: str) -> List[Content]:
        """Get detailed status for a specific VM.

        Args:
            node: Host node name (e.g. 'pve1')
            vmid: VM ID (e.g. '100')

        Returns:
            List of Content objects with formatted VM status.

        Raises:
            ValueError: If the VM is not found
            RuntimeError: If status retrieval fails
        """
        try:
            status = self.proxmox.nodes(node).qemu(vmid).status.current.get()
            return self._format_response((vmid, status), "vm_status")
        except Exception as e:
            self._handle_error(f"get status for VM {vmid}", e)

    def _lifecycle_action(self, node: str, vmid: str, action: str) -> List[Content]:
        """Perform a lifecycle action (start/stop/shutdown/reboot) on a VM.

        Args:
            node: Host node name
            vmid: VM ID
            action: One of 'start', 'stop', 'shutdown', 'reboot'

        Returns:
            List of Content objects with the task ID returned by Proxmox.
        """
        try:
            endpoint = getattr(self.proxmox.nodes(node).qemu(vmid).status, action)
            task_id = endpoint.post()
            text = f"VM {vmid} {action} initiated\nTask ID: {task_id}"
            from mcp.types import TextContent
            return [TextContent(type="text", text=text)]
        except Exception as e:
            self._handle_error(f"{action} VM {vmid}", e)

    def start_vm(self, node: str, vmid: str) -> List[Content]:
        """Start a stopped virtual machine."""
        return self._lifecycle_action(node, vmid, "start")

    def stop_vm(self, node: str, vmid: str) -> List[Content]:
        """Immediately stop a running virtual machine (hard stop)."""
        return self._lifecycle_action(node, vmid, "stop")

    def shutdown_vm(self, node: str, vmid: str) -> List[Content]:
        """Gracefully shut down a running virtual machine."""
        return self._lifecycle_action(node, vmid, "shutdown")

    def reboot_vm(self, node: str, vmid: str) -> List[Content]:
        """Reboot a running virtual machine."""
        return self._lifecycle_action(node, vmid, "reboot")

    def clone_vm(
        self,
        node: str,
        vmid: str,
        newid: str,
        name: Optional[str] = None,
        target: Optional[str] = None,
        full: bool = True,
    ) -> List[Content]:
        """Clone a virtual machine or template to a new VM.

        Args:
            node: Host node name (e.g. 'pve1')
            vmid: Source VM/template ID
            newid: New VM ID for the clone
            name: Optional name for the new VM
            target: Optional target node (defaults to same node)
            full: Full clone if True, linked clone if False

        Returns:
            List of Content objects with the new VM ID and task ID.

        Raises:
            ValueError: If the source VM is not found
            RuntimeError: If the clone operation fails
        """
        try:
            params = {"newid": int(newid), "full": 1 if full else 0}
            if name:
                params["name"] = name
            if target:
                params["target"] = target
            task_id = self.proxmox.nodes(node).qemu(vmid).clone.post(**params)
            from mcp.types import TextContent
            text = f"VM {vmid} clone initiated\nNew VM ID: {newid}\nTask ID: {task_id}"
            return [TextContent(type="text", text=text)]
        except Exception as e:
            self._handle_error(f"clone VM {vmid}", e)

    async def execute_command(self, node: str, vmid: str, command: str) -> List[Content]:
        """Execute a command in a VM via QEMU guest agent.

        Uses the QEMU guest agent to execute commands within a running VM.
        Requires:
        - VM must be running
        - QEMU guest agent must be installed and running in the VM
        - Command execution permissions must be enabled

        Args:
            node: Host node name (e.g., 'pve1', 'proxmox-node2')
            vmid: VM ID number (e.g., '100', '101')
            command: Shell command to run (e.g., 'uname -a', 'systemctl status nginx')

        Returns:
            List of Content objects containing formatted command output:
            {
                "success": true/false,
                "output": "command output",
                "error": "error message if any"
            }

        Raises:
            ValueError: If VM is not found, not running, or guest agent is not available
            RuntimeError: If command execution fails due to permissions or other issues
        """
        try:
            result = await self.console_manager.execute_command(node, vmid, command)
            # Use the command output formatter from ProxmoxFormatters
            from ..formatting import ProxmoxFormatters
            formatted = ProxmoxFormatters.format_command_output(
                success=result["success"],
                command=command,
                output=result["output"],
                error=result.get("error")
            )
            return [Content(type="text", text=formatted)]
        except Exception as e:
            self._handle_error(f"execute command on VM {vmid}", e)
