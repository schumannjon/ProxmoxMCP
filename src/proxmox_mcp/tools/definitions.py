"""
Tool descriptions for Proxmox MCP tools.
"""

# Node tool descriptions
GET_NODES_DESC = """List all nodes in the Proxmox cluster with their status, CPU, memory, and role information.

Example:
{"node": "pve1", "status": "online", "cpu_usage": 0.15, "memory": {"used": "8GB", "total": "32GB"}}"""

GET_NODE_STATUS_DESC = """Get detailed status information for a specific Proxmox node.

Parameters:
node* - Name/ID of node to query (e.g. 'pve1')

Example:
{"cpu": {"usage": 0.15}, "memory": {"used": "8GB", "total": "32GB"}}"""

# VM tool descriptions
GET_VMS_DESC = """List all virtual machines across the cluster with their status and resource usage.

Example:
{"vmid": "100", "name": "ubuntu", "status": "running", "cpu": 2, "memory": 4096}"""

EXECUTE_VM_COMMAND_DESC = """Execute commands in a VM via QEMU guest agent.

Parameters:
node* - Host node name (e.g. 'pve1')
vmid* - VM ID number (e.g. '100')
command* - Shell command to run (e.g. 'uname -a')

Example:
{"success": true, "output": "Linux vm1 5.4.0", "exit_code": 0}"""

# Container tool descriptions
GET_CONTAINERS_DESC = """List all LXC containers across the cluster with their status and configuration.

Example:
{"vmid": "200", "name": "nginx", "status": "running", "template": "ubuntu-20.04"}"""

GET_CONTAINER_STATUS_DESC = """Get detailed status for a specific LXC container.

Parameters:
node* - Host node name (e.g. 'pve1')
vmid* - Container ID number (e.g. '200')

Example:
{"status": "running", "uptime": 3600, "cpu": 0.02, "mem": 134217728, "maxmem": 536870912}"""

START_CONTAINER_DESC = """Start a stopped LXC container.

Parameters:
node* - Host node name (e.g. 'pve1')
vmid* - Container ID number (e.g. '200')

Example:
{"task": "UPID:pve1:...", "status": "started"}"""

STOP_CONTAINER_DESC = """Immediately stop a running LXC container (hard stop, no graceful shutdown).

Parameters:
node* - Host node name (e.g. 'pve1')
vmid* - Container ID number (e.g. '200')

Example:
{"task": "UPID:pve1:...", "status": "stopped"}"""

SHUTDOWN_CONTAINER_DESC = """Gracefully shut down a running LXC container.

Parameters:
node* - Host node name (e.g. 'pve1')
vmid* - Container ID number (e.g. '200')

Example:
{"task": "UPID:pve1:...", "status": "shutdown initiated"}"""

REBOOT_CONTAINER_DESC = """Reboot a running LXC container.

Parameters:
node* - Host node name (e.g. 'pve1')
vmid* - Container ID number (e.g. '200')

Example:
{"task": "UPID:pve1:...", "status": "reboot initiated"}"""


# Storage tool descriptions
GET_STORAGE_DESC = """List storage pools across the cluster with their usage and configuration.

Example:
{"storage": "local-lvm", "type": "lvm", "used": "500GB", "total": "1TB"}"""

# Cluster tool descriptions
GET_CLUSTER_STATUS_DESC = """Get overall Proxmox cluster health and configuration status.

Example:
{"name": "proxmox", "quorum": "ok", "nodes": 3, "ha_status": "active"}"""
