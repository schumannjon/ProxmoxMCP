"""
Tests for config loading logic in loader.py.

Covers:
- env-var path (happy path + missing vars + optional defaults)
- JSON file path
- error when neither source is available
"""
import json
import os
import pytest
from unittest.mock import patch

from proxmox_mcp.config.loader import load_config


# ---------------------------------------------------------------------------
# No configuration available
# ---------------------------------------------------------------------------

def test_no_config_raises_clear_error():
    """Both sources absent → error mentions both options."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="PROXMOX_MCP_CONFIG"):
            load_config()


# ---------------------------------------------------------------------------
# Env-var path
# ---------------------------------------------------------------------------

REQUIRED_ENV = {
    "PROXMOX_HOST": "192.168.1.1",
    "PROXMOX_USER": "root@pam",
    "PROXMOX_TOKEN_NAME": "mytoken",
    "PROXMOX_TOKEN_VALUE": "secret",
}


def test_env_var_happy_path():
    """All required vars present → Config populated correctly."""
    with patch.dict(os.environ, REQUIRED_ENV, clear=True):
        cfg = load_config()
    assert cfg.proxmox.host == "192.168.1.1"
    assert cfg.auth.user == "root@pam"
    assert cfg.auth.token_name == "mytoken"
    assert cfg.auth.token_value == "secret"


def test_env_var_optional_defaults():
    """Optional vars default correctly when absent."""
    with patch.dict(os.environ, REQUIRED_ENV, clear=True):
        cfg = load_config()
    assert cfg.proxmox.port == 8006
    assert cfg.proxmox.verify_ssl is True
    assert cfg.proxmox.service == "PVE"
    assert cfg.logging.level == "INFO"


def test_env_var_optional_overrides():
    """Optional vars are respected when provided."""
    env = {
        **REQUIRED_ENV,
        "PROXMOX_PORT": "9000",
        "PROXMOX_VERIFY_SSL": "false",
        "PROXMOX_SERVICE": "PBS",
        "LOG_LEVEL": "DEBUG",
    }
    with patch.dict(os.environ, env, clear=True):
        cfg = load_config()
    assert cfg.proxmox.port == 9000
    assert cfg.proxmox.verify_ssl is False
    assert cfg.proxmox.service == "PBS"
    assert cfg.logging.level == "DEBUG"


@pytest.mark.parametrize("verify_ssl_value,expected", [
    ("false", False),
    ("False", False),
    ("FALSE", False),
    ("0", False),
    ("no", False),
    ("true", True),
    ("True", True),
    ("1", True),
    ("yes", True),
])
def test_env_var_verify_ssl_parsing(verify_ssl_value, expected):
    """PROXMOX_VERIFY_SSL string values parsed correctly."""
    env = {**REQUIRED_ENV, "PROXMOX_VERIFY_SSL": verify_ssl_value}
    with patch.dict(os.environ, env, clear=True):
        cfg = load_config()
    assert cfg.proxmox.verify_ssl is expected


def test_env_var_missing_all_required():
    """PROXMOX_HOST set but all others missing → error lists all missing vars."""
    with patch.dict(os.environ, {"PROXMOX_HOST": "h"}, clear=True):
        with pytest.raises(ValueError) as exc_info:
            load_config()
    msg = str(exc_info.value)
    assert "PROXMOX_USER" in msg
    assert "PROXMOX_TOKEN_NAME" in msg
    assert "PROXMOX_TOKEN_VALUE" in msg


def test_env_var_missing_one_required():
    """One required var absent → error names that var."""
    env = {k: v for k, v in REQUIRED_ENV.items() if k != "PROXMOX_TOKEN_VALUE"}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ValueError, match="PROXMOX_TOKEN_VALUE"):
            load_config()


# ---------------------------------------------------------------------------
# JSON file path
# ---------------------------------------------------------------------------

def test_json_file_happy_path(tmp_path):
    """Valid JSON config file loads correctly."""
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({
        "proxmox": {"host": "10.0.0.1"},
        "auth": {"user": "admin@pam", "token_name": "t", "token_value": "v"},
        "logging": {"level": "WARNING"},
    }))
    cfg = load_config(str(cfg_file))
    assert cfg.proxmox.host == "10.0.0.1"
    assert cfg.logging.level == "WARNING"


def test_json_file_takes_priority_over_env(tmp_path):
    """config_path wins even when PROXMOX_HOST is also set."""
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({
        "proxmox": {"host": "from-file"},
        "auth": {"user": "u", "token_name": "t", "token_value": "v"},
        "logging": {},
    }))
    env = {**REQUIRED_ENV, "PROXMOX_HOST": "from-env"}
    with patch.dict(os.environ, env, clear=True):
        cfg = load_config(str(cfg_file))
    assert cfg.proxmox.host == "from-file"


def test_json_file_missing_host_raises():
    """JSON config with empty host raises ValueError."""
    import tempfile, json as _json
    data = {
        "proxmox": {"host": ""},
        "auth": {"user": "u", "token_name": "t", "token_value": "v"},
        "logging": {},
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        _json.dump(data, f)
        path = f.name
    with pytest.raises(ValueError, match="host"):
        load_config(path)


def test_json_file_invalid_json(tmp_path):
    """Malformed JSON raises ValueError."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{ not valid json }")
    with pytest.raises(ValueError, match="Invalid JSON"):
        load_config(str(bad_file))


def test_json_file_not_found():
    """Non-existent file raises ValueError."""
    with pytest.raises(ValueError, match="Failed to load config"):
        load_config("/nonexistent/path/config.json")
