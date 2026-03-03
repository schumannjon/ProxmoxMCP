"""
Output templates for Proxmox MCP resource types.
"""
from typing import Dict, List, Any
from .formatters import ProxmoxFormatters
from .theme import ProxmoxTheme
from .colors import ProxmoxColors
from .components import ProxmoxComponents

class ProxmoxTemplates:
    """Output templates for different Proxmox resource types."""
    
    @staticmethod
    def node_list(nodes: List[Dict[str, Any]]) -> str:
        """Template for node list output.
        
        Args:
            nodes: List of node data dictionaries
            
        Returns:
            Formatted node list string
        """
        result = [f"{ProxmoxTheme.RESOURCES['node']} Proxmox Nodes"]
        
        for node in nodes:
            # Get node status
            status = node.get("status", "unknown")
            
            # Get memory info
            memory = node.get("memory", {})
            memory_used = memory.get("used", 0)
            memory_total = memory.get("total", 0)
            memory_percent = (memory_used / memory_total * 100) if memory_total > 0 else 0
            
            # Format node info
            result.extend([
                "",  # Empty line between nodes
                f"{ProxmoxTheme.RESOURCES['node']} {node['node']}",
                f"  • Status: {status.upper()}",
                f"  • Uptime: {ProxmoxFormatters.format_uptime(node.get('uptime', 0))}",
                f"  • CPU Cores: {node.get('maxcpu', 'N/A')}",
                f"  • Memory: {ProxmoxFormatters.format_bytes(memory_used)} / "
                f"{ProxmoxFormatters.format_bytes(memory_total)} ({memory_percent:.1f}%)"
            ])
            
            # Add disk usage if available
            disk = node.get("disk", {})
            if disk:
                disk_used = disk.get("used", 0)
                disk_total = disk.get("total", 0)
                disk_percent = (disk_used / disk_total * 100) if disk_total > 0 else 0
                result.append(
                    f"  • Disk: {ProxmoxFormatters.format_bytes(disk_used)} / "
                    f"{ProxmoxFormatters.format_bytes(disk_total)} ({disk_percent:.1f}%)"
                )
            
        return "\n".join(result)
    
    @staticmethod
    def node_status(node: str, status: Dict[str, Any]) -> str:
        """Template for detailed node status output.
        
        Args:
            node: Node name
            status: Node status data
            
        Returns:
            Formatted node status string
        """
        memory = status.get("memory", {})
        memory_used = memory.get("used", 0)
        memory_total = memory.get("total", 0)
        memory_percent = (memory_used / memory_total * 100) if memory_total > 0 else 0
        
        result = [
            f"{ProxmoxTheme.RESOURCES['node']} Node: {node}",
            f"  • Status: {status.get('status', 'unknown').upper()}",
            f"  • Uptime: {ProxmoxFormatters.format_uptime(status.get('uptime', 0))}",
            f"  • CPU Cores: {status.get('maxcpu', 'N/A')}",
            f"  • Memory: {ProxmoxFormatters.format_bytes(memory_used)} / "
            f"{ProxmoxFormatters.format_bytes(memory_total)} ({memory_percent:.1f}%)"
        ]
        
        # Add disk usage if available
        disk = status.get("disk", {})
        if disk:
            disk_used = disk.get("used", 0)
            disk_total = disk.get("total", 0)
            disk_percent = (disk_used / disk_total * 100) if disk_total > 0 else 0
            result.append(
                f"  • Disk: {ProxmoxFormatters.format_bytes(disk_used)} / "
                f"{ProxmoxFormatters.format_bytes(disk_total)} ({disk_percent:.1f}%)"
            )
        
        return "\n".join(result)
    
    @staticmethod
    def vm_list(vms: List[Dict[str, Any]]) -> str:
        """Template for VM list output.
        
        Args:
            vms: List of VM data dictionaries
            
        Returns:
            Formatted VM list string
        """
        result = [f"{ProxmoxTheme.RESOURCES['vm']} Virtual Machines"]
        
        for vm in vms:
            memory = vm.get("memory", {})
            memory_used = memory.get("used", 0)
            memory_total = memory.get("total", 0)
            memory_percent = (memory_used / memory_total * 100) if memory_total > 0 else 0
            
            result.extend([
                "",  # Empty line between VMs
                f"{ProxmoxTheme.RESOURCES['vm']} {vm['name']} (ID: {vm['vmid']})",
                f"  • Status: {vm['status'].upper()}",
                f"  • Node: {vm['node']}",
                f"  • CPU Cores: {vm.get('cpus', 'N/A')}",
                f"  • Memory: {ProxmoxFormatters.format_bytes(memory_used)} / "
                f"{ProxmoxFormatters.format_bytes(memory_total)} ({memory_percent:.1f}%)"
            ])
            
        return "\n".join(result)
    
    @staticmethod
    def storage_list(storage: List[Dict[str, Any]]) -> str:
        """Template for storage list output.
        
        Args:
            storage: List of storage data dictionaries
            
        Returns:
            Formatted storage list string
        """
        result = [f"{ProxmoxTheme.RESOURCES['storage']} Storage Pools"]
        
        for store in storage:
            used = store.get("used", 0)
            total = store.get("total", 0)
            percent = (used / total * 100) if total > 0 else 0
            
            result.extend([
                "",  # Empty line between storage pools
                f"{ProxmoxTheme.RESOURCES['storage']} {store['storage']}",
                f"  • Status: {store.get('status', 'unknown').upper()}",
                f"  • Type: {store['type']}",
                f"  • Usage: {ProxmoxFormatters.format_bytes(used)} / "
                f"{ProxmoxFormatters.format_bytes(total)} ({percent:.1f}%)"
            ])
            
        return "\n".join(result)
    
    @staticmethod
    def _parse_config_string(value: str) -> Dict[str, str]:
        """Parse a Proxmox config string like 'key=val,key2=val2' into a dict.

        The first token may be a bare volume/device string with no '='.
        """
        result = {}
        for token in value.split(","):
            if "=" in token:
                k, _, v = token.partition("=")
                result[k.strip()] = v.strip()
            else:
                result["volume"] = token.strip()
        return result

    @staticmethod
    def container_config(vmid: str, config: Dict[str, Any]) -> str:
        """Template for LXC container configuration output.

        Args:
            vmid: Container ID
            config: Container config data from the Proxmox API

        Returns:
            Formatted container config string
        """
        result = [
            f"{ProxmoxTheme.RESOURCES['container']} Config: "
            f"{config.get('hostname', vmid)} (ID: {vmid})"
        ]

        # Identity
        result.append("\n  Identity")
        result.append(f"  • Hostname:     {config.get('hostname', 'N/A')}")
        result.append(f"  • OS Type:      {config.get('ostype', 'N/A')}")
        result.append(f"  • Unprivileged: {'yes' if config.get('unprivileged') else 'no'}")
        result.append(f"  • On Boot:      {'yes' if config.get('onboot') else 'no'}")
        if config.get("tags"):
            result.append(f"  • Tags:         {config['tags']}")
        if config.get("description"):
            result.append(f"  • Description:  {config['description'].strip()}")

        # Resources
        result.append("\n  Resources")
        result.append(f"  • CPU Cores:    {config.get('cores', 'N/A')}")
        if config.get("cpulimit"):
            result.append(f"  • CPU Limit:    {config['cpulimit']}")
        result.append(f"  • Memory:       {config.get('memory', 'N/A')} MB")
        result.append(f"  • Swap:         {config.get('swap', 0)} MB")

        # Storage — rootfs + any mount points
        result.append("\n  Storage")
        if config.get("rootfs"):
            parsed = ProxmoxTemplates._parse_config_string(config["rootfs"])
            vol = parsed.get("volume", config["rootfs"])
            size = parsed.get("size", "?")
            result.append(f"  • Root FS:      {vol} ({size})")
        for i in range(10):
            mp_key = f"mp{i}"
            if config.get(mp_key):
                parsed = ProxmoxTemplates._parse_config_string(config[mp_key])
                vol = parsed.get("volume", "?")
                mp = parsed.get("mp", "?")
                size = parsed.get("size", "?")
                result.append(f"  • mp{i}:          {vol} → {mp} ({size})")

        # Network interfaces
        result.append("\n  Network")
        found_net = False
        for i in range(10):
            net_key = f"net{i}"
            if config.get(net_key):
                found_net = True
                parsed = ProxmoxTemplates._parse_config_string(config[net_key])
                name = parsed.get("name", net_key)
                bridge = parsed.get("bridge", "?")
                ip = parsed.get("ip", "dhcp")
                ip6 = parsed.get("ip6", "")
                gw = parsed.get("gw", "")
                line = f"  • {name} ({net_key}): bridge={bridge}, ip={ip}"
                if ip6:
                    line += f", ip6={ip6}"
                if gw:
                    line += f", gw={gw}"
                result.append(line)
        if not found_net:
            result.append("  • No network interfaces configured")

        # Features
        if config.get("features"):
            result.append(f"\n  Features: {config['features']}")

        return "\n".join(result)

    @staticmethod
    def container_status(vmid: str, status: Dict[str, Any]) -> str:
        """Template for detailed container status output.

        Args:
            vmid: Container ID
            status: Container status data

        Returns:
            Formatted container status string
        """
        memory_used = status.get("mem", 0)
        memory_total = status.get("maxmem", 0)
        memory_percent = (memory_used / memory_total * 100) if memory_total > 0 else 0

        disk_used = status.get("disk", 0)
        disk_total = status.get("maxdisk", 0)
        disk_percent = (disk_used / disk_total * 100) if disk_total > 0 else 0

        cpu_percent = status.get("cpu", 0) * 100

        result = [
            f"{ProxmoxTheme.RESOURCES['container']} Container: {status.get('name', vmid)} (ID: {vmid})",
            f"  • Status: {status.get('status', 'unknown').upper()}",
            f"  • Uptime: {ProxmoxFormatters.format_uptime(status.get('uptime', 0))}",
            f"  • CPU Cores: {status.get('cpus', 'N/A')}",
            f"  • CPU Usage: {cpu_percent:.1f}%",
            f"  • Memory: {ProxmoxFormatters.format_bytes(memory_used)} / "
            f"{ProxmoxFormatters.format_bytes(memory_total)} ({memory_percent:.1f}%)",
            f"  • Disk: {ProxmoxFormatters.format_bytes(disk_used)} / "
            f"{ProxmoxFormatters.format_bytes(disk_total)} ({disk_percent:.1f}%)",
        ]

        return "\n".join(result)

    @staticmethod
    def container_list(containers: List[Dict[str, Any]]) -> str:
        """Template for container list output.
        
        Args:
            containers: List of container data dictionaries
            
        Returns:
            Formatted container list string
        """
        if not containers:
            return f"{ProxmoxTheme.RESOURCES['container']} No containers found"
            
        result = [f"{ProxmoxTheme.RESOURCES['container']} Containers"]
        
        for container in containers:
            memory = container.get("memory", {})
            memory_used = memory.get("used", 0)
            memory_total = memory.get("total", 0)
            memory_percent = (memory_used / memory_total * 100) if memory_total > 0 else 0
            
            result.extend([
                "",  # Empty line between containers
                f"{ProxmoxTheme.RESOURCES['container']} {container['name']} (ID: {container['vmid']})",
                f"  • Status: {container['status'].upper()}",
                f"  • Node: {container['node']}",
                f"  • CPU Cores: {container.get('cpus', 'N/A')}",
                f"  • Memory: {ProxmoxFormatters.format_bytes(memory_used)} / "
                f"{ProxmoxFormatters.format_bytes(memory_total)} ({memory_percent:.1f}%)"
            ])
            
        return "\n".join(result)

    @staticmethod
    def cluster_status(status: Dict[str, Any]) -> str:
        """Template for cluster status output.
        
        Args:
            status: Cluster status data
            
        Returns:
            Formatted cluster status string
        """
        result = [f"{ProxmoxTheme.SECTIONS['configuration']} Proxmox Cluster"]
        
        # Basic cluster info
        result.extend([
            "",
            f"  • Name: {status.get('name', 'N/A')}",
            f"  • Quorum: {'OK' if status.get('quorum') else 'NOT OK'}",
            f"  • Nodes: {status.get('nodes', 0)}",
        ])
        
        # Add resource count if available
        resources = status.get('resources', [])
        if resources:
            result.append(f"  • Resources: {len(resources)}")
        
        return "\n".join(result)
