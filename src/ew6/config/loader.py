from __future__ import annotations

from typing import Any, Dict, Optional

from .providers import ConfigManager, DictProvider, EnvProvider, FileProvider


def load_config(
    defaults: Optional[Dict[str, Any]] = None,
    file_path: Optional[str] = None,
    *,
    use_env: bool = True,
    env_prefix: str = "EW6_",
) -> Dict[str, Any]:
    """Load layered config: defaults < file < env.

    This keeps the old signature used across the project while internally using
    the provider interface so V2 can plug DB-backed configs cleanly.
    """
    providers = [DictProvider(data=dict(defaults or {}))]
    if file_path:
        providers.append(FileProvider(path=file_path, optional=True))
    if use_env:
        providers.append(EnvProvider(prefix=env_prefix))
    return ConfigManager(providers).load()
