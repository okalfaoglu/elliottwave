"""Config module.

Existing API:
  - load_config(defaults: dict, file_path: Optional[str]) -> dict

Added in v0.7.0:
  - providers interface for V2 DB-backed config
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# Keep existing imports working
from .loader import load_config  # noqa: F401

# Provider API (V2-ready)
from .providers import (  # noqa: F401
    ConfigProvider,
    ConfigManager,
    DictProvider,
    EnvProvider,
    FileProvider,
    DBProvider,
)

__all__ = [
    "load_config",
    "ConfigProvider",
    "ConfigManager",
    "DictProvider",
    "EnvProvider",
    "FileProvider",
    "DBProvider",
]
