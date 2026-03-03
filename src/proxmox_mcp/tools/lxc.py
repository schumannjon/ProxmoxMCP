"""
LXC container tools for Proxmox MCP.

This module provides tools for managing and inspecting Proxmox LXC containers:
- Listing all containers across the cluster with their status
- Retrieving detailed container status
- Lifecycle controls (start, stop, shutdown, reboot)
"""
from typing import List
from mcp.types import TextContent as Content
from .base import ProxmoxTool
from .definitions import (
    GET_CONTAINERS_DESC,
    GET_CONTAINER_STATUS_DESC,
    START_CONTAINER_DESC,
    STOP_CONTAINER_DESC,
    SHUTDOWN_CONTAINER_DESC,
    REBOOT_CONTAINER_DESC,
)


class LXCTools(ProxmoxTool):
    """Tools for managing Proxmox LXC containers."""

    def get_containers(self) -> List[Content]:
        """List all LXC containers across the cluster with detailed status.

        Returns:
            List of Content objects containing formatted container information.

        Raises:
            RuntimeError: If the cluster-wide container query fails
        """
        try:
            result = []
            for node in self.proxmox.nodes.get():
                node_name = node["node"]
                containers = self.proxmox.nodes(node_name).lxc.get()
                for ct in containers:
                    vmid = ct["vmid"]
                    try:
                        config = self.proxmox.nodes(node_name).lxc(vmid).config.get()
                        result.append({
                            "vmid": vmid,
                            "name": ct.get("name", f"CT-{vmid}"),
                            "status": ct["status"],
                            "node": node_name,
                            "cpus": config.get("cores", "N/A"),
                            "memory": {
                                "used": ct.get("mem", 0),
                                "total": ct.get("maxmem", 0),
                            },
                        })
                    except Exception:
                        result.append({
                            "vmid": vmid,
                            "name": ct.get("name", f"CT-{vmid}"),
                            "status": ct["status"],
                            "node": node_name,
                            "cpus": "N/A",
                            "memory": {
                                "used": ct.get("mem", 0),
                                "total": ct.get("maxmem", 0),
                            },
                        })
            return self._format_response(result, "containers")
        except Exception as e:
            self._handle_error("get LXC containers", e)

    def get_container_status(self, node: str, vmid: str) -> List[Content]:
        """Get detailed status for a specific LXC container.

        Args:
            node: Host node name (e.g. 'pve1')
            vmid: Container ID (e.g. '200')

        Returns:
            List of Content objects with formatted container status.

        Raises:
            ValueError: If the container is not found
            RuntimeError: If status retrieval fails
        """
        try:
            status = self.proxmox.nodes(node).lxc(vmid).status.current.get()
            return self._format_response((vmid, status), "container_status")
        except Exception as e:
            self._handle_error(f"get status for container {vmid}", e)

    def _lifecycle_action(self, node: str, vmid: str, action: str) -> List[Content]:
        """Perform a lifecycle action (start/stop/shutdown/reboot) on a container.

        Args:
            node: Host node name
            vmid: Container ID
            action: One of 'start', 'stop', 'shutdown', 'reboot'

        Returns:
            List of Content objects with the task ID returned by Proxmox.
        """
        try:
            endpoint = getattr(self.proxmox.nodes(node).lxc(vmid).status, action)
            task_id = endpoint.post()
            text = f"Container {vmid} {action} initiated\nTask ID: {task_id}"
            from mcp.types import TextContent
            return [TextContent(type="text", text=text)]
        except Exception as e:
            self._handle_error(f"{action} container {vmid}", e)

    def start_container(self, node: str, vmid: str) -> List[Content]:
        """Start a stopped LXC container."""
        return self._lifecycle_action(node, vmid, "start")

    def stop_container(self, node: str, vmid: str) -> List[Content]:
        """Immediately stop a running LXC container (hard stop)."""
        return self._lifecycle_action(node, vmid, "stop")

    def shutdown_container(self, node: str, vmid: str) -> List[Content]:
        """Gracefully shut down a running LXC container."""
        return self._lifecycle_action(node, vmid, "shutdown")

    def reboot_container(self, node: str, vmid: str) -> List[Content]:
        """Reboot a running LXC container."""
        return self._lifecycle_action(node, vmid, "reboot")
