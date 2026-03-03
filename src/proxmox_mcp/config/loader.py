"""
Configuration loading utilities for the Proxmox MCP server.

This module handles loading and validation of server configuration:
- JSON configuration file loading
- Environment variable handling
- Configuration validation using Pydantic models
- Error handling for invalid configurations

The module ensures that all required configuration is present
and valid before the server starts operation.
"""
import json
import os
from typing import Optional
from .models import Config, ProxmoxConfig, AuthConfig, LoggingConfig


def load_config(config_path: Optional[str] = None) -> Config:
    """Load and validate configuration from a JSON file or environment variables.

    Priority:
    1. If ``config_path`` is provided, load from the JSON file (existing behaviour).
    2. Else if ``PROXMOX_HOST`` is set, build ``Config`` from environment variables.
    3. Else raise a ``ValueError`` explaining both options.

    Environment variables (used when no config file is provided):
    - PROXMOX_HOST        (required)
    - PROXMOX_USER        (required)
    - PROXMOX_TOKEN_NAME  (required)
    - PROXMOX_TOKEN_VALUE (required)
    - PROXMOX_PORT        (optional, default 8006)
    - PROXMOX_VERIFY_SSL  (optional, default "true"; set to "false" to disable)
    - PROXMOX_SERVICE     (optional, default "PVE")
    - LOG_LEVEL           (optional, default "INFO")

    Args:
        config_path: Path to the JSON configuration file.

    Returns:
        Validated ``Config`` object.

    Raises:
        ValueError: If configuration is missing or invalid.
    """
    if config_path:
        return _load_from_file(config_path)

    if os.environ.get("PROXMOX_HOST"):
        return _load_from_env()

    raise ValueError(
        "No configuration found. Either:\n"
        "  - Set PROXMOX_MCP_CONFIG to a JSON config file path, or\n"
        "  - Set PROXMOX_HOST (plus PROXMOX_USER, PROXMOX_TOKEN_NAME, PROXMOX_TOKEN_VALUE)"
    )


def _load_from_file(config_path: str) -> Config:
    """Load configuration from a JSON file."""
    try:
        with open(config_path) as f:
            config_data = json.load(f)
            if not config_data.get("proxmox", {}).get("host"):
                raise ValueError("Proxmox host cannot be empty")
            return Config(**config_data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file: {e}")
    except Exception as e:
        raise ValueError(f"Failed to load config: {e}")


def _load_from_env() -> Config:
    """Build configuration from environment variables."""
    required = {
        "PROXMOX_HOST": os.environ.get("PROXMOX_HOST"),
        "PROXMOX_USER": os.environ.get("PROXMOX_USER"),
        "PROXMOX_TOKEN_NAME": os.environ.get("PROXMOX_TOKEN_NAME"),
        "PROXMOX_TOKEN_VALUE": os.environ.get("PROXMOX_TOKEN_VALUE"),
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    verify_ssl_raw = os.environ.get("PROXMOX_VERIFY_SSL", "true").lower()
    verify_ssl = verify_ssl_raw not in ("false", "0", "no")

    return Config(
        proxmox=ProxmoxConfig(
            host=required["PROXMOX_HOST"],  # type: ignore[arg-type]
            port=int(os.environ.get("PROXMOX_PORT", "8006")),
            verify_ssl=verify_ssl,
            service=os.environ.get("PROXMOX_SERVICE", "PVE"),
        ),
        auth=AuthConfig(
            user=required["PROXMOX_USER"],  # type: ignore[arg-type]
            token_name=required["PROXMOX_TOKEN_NAME"],  # type: ignore[arg-type]
            token_value=required["PROXMOX_TOKEN_VALUE"],  # type: ignore[arg-type]
        ),
        logging=LoggingConfig(
            level=os.environ.get("LOG_LEVEL", "INFO"),
        ),
    )
