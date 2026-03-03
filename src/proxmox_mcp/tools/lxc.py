"""
LXC container tools for Proxmox MCP.

This module provides tools for managing and inspecting Proxmox LXC containers:
- Listing all containers across the cluster with their status
- Retrieving container details including:
  * Resource allocation (CPU, memory)
  * Runtime status
  * Node placement
"""
from typing import List
from mcp.types import TextContent as Content
from .base import ProxmoxTool
from .definitions import GET_CONTAINERS_DESC


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
