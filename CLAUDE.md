# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install with dev dependencies (use uv, not pip)
uv pip install -e ".[dev]"

# Run all tests
pytest

# Run a single test file
pytest tests/test_server.py -v

# Run a single test by name
pytest tests/test_server.py::test_get_nodes -v

# Format
black .

# Lint
ruff .

# Type check
mypy .

# Run the server (requires config file)
PROXMOX_MCP_CONFIG="proxmox-config/config.json" python -m proxmox_mcp.server
```

## Docker

```bash
# Build
docker build -t proxmox-mcp .

# Run with env vars
docker run --rm -i \
  -e PROXMOX_HOST=192.168.1.100 \
  -e PROXMOX_USER=root@pam \
  -e PROXMOX_TOKEN_NAME=mcp-token \
  -e PROXMOX_TOKEN_VALUE=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx \
  proxmox-mcp

# Run with env file (keeps secrets out of process args)
docker run --rm -i --env-file .env proxmox-mcp
```

MCP client config (stdio transport):
```json
{
  "command": "docker",
  "args": ["run", "--rm", "-i",
    "-e", "PROXMOX_HOST=192.168.1.100",
    "-e", "PROXMOX_USER=root@pam",
    "-e", "PROXMOX_TOKEN_NAME=mcp-token",
    "-e", "PROXMOX_TOKEN_VALUE=xxx",
    "proxmox-mcp"
  ]
}
```

## Architecture

This is a **Model Context Protocol (MCP) server** that exposes Proxmox hypervisor management as MCP tools, consumed by AI clients like Cline. It uses the `FastMCP` framework from the official MCP Python SDK and communicates over stdio.

### Startup flow

`server.py` → `load_config()` (reads `PROXMOX_MCP_CONFIG` env var → JSON file) → `ProxmoxManager` (creates and tests `ProxmoxAPI` connection) → tool classes instantiated → `FastMCP` tools registered → `anyio.run(mcp.run_stdio_async)`

### Tool layer (`src/proxmox_mcp/tools/`)

All tool classes inherit from `ProxmoxTool` (`base.py`), which provides:
- `self.proxmox` — the live `ProxmoxAPI` instance
- `_format_response(data, resource_type)` — routes to the correct `ProxmoxTemplates` formatter
- `_handle_error(operation, error)` — classifies errors as `ValueError` or `RuntimeError`

| Class | File | Registered tools |
|---|---|---|
| `NodeTools` | `node.py` | `get_nodes`, `get_node_status` |
| `VMTools` | `vm.py` | `get_vms`, `execute_vm_command` |
| `StorageTools` | `storage.py` | `get_storage` |
| `ClusterTools` | `cluster.py` | `get_cluster_status` |

`VMTools` delegates console/QEMU agent operations to `VMConsoleManager` (`tools/console/manager.py`). VM command execution is `async`; all other tools are sync.

### Formatting layer (`src/proxmox_mcp/formatting/`)

- `ProxmoxTheme` — emoji and section constants
- `ProxmoxColors` — ANSI color helpers with metric thresholds (warn at 80%, critical at 90%)
- `ProxmoxFormatters` — stateless formatting utilities (bytes, uptime, percentages, command output)
- `ProxmoxTemplates` — high-level templates that compose the above into full resource displays (`node_list`, `vm_list`, `cluster_status`, etc.)
- `ProxmoxComponents` — reusable block builders used by templates

### Configuration (`src/proxmox_mcp/config/`)

Config is a JSON file path passed via `PROXMOX_MCP_CONFIG`. Pydantic models validate the three sections: `ProxmoxConfig` (connection), `AuthConfig` (API token), `LoggingConfig`. Authentication is always token-based (no password auth).

### Testing

Tests use `unittest.mock` to patch `ProxmoxAPI` and a `pytest-asyncio` fixture chain (`mock_env_vars` → `mock_proxmox` → `server`). `asyncio_mode = "strict"` is set in `pyproject.toml`, so async tests must use `@pytest.mark.asyncio`. The `get_containers` tool is tested but not currently registered in `server.py`.
