"""Config provider interface (V2-ready).

M1 requirement: layered config (defaults < file < env < CLI) already exists.
This module adds a provider abstraction so that later we can plug DB-backed
dynamic config without touching the app code.

Design:
  - Provider returns a dict-like config payload.
  - ConfigManager composes multiple providers with precedence order.
  - Optional periodic refresh can be implemented by providers (V2).

NOTE: Keep dependencies minimal (stdlib only).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Protocol, runtime_checkable
import json
import os


@runtime_checkable
class ConfigProvider(Protocol):
    name: str

    def load(self) -> Dict[str, Any]:
        """Return the provider config as a plain dict."""
        ...


def _deep_merge(a: Dict[str, Any], b: Mapping[str, Any]) -> Dict[str, Any]:
    """Merge mapping b into dict a (recursive for dict values)."""
    for k, v in b.items():
        if isinstance(v, Mapping) and isinstance(a.get(k), Mapping):
            a[k] = _deep_merge(dict(a[k]), v)  # type: ignore[arg-type]
        else:
            a[k] = v
    return a


def _set_nested(d: Dict[str, Any], keys: List[str], value: Any) -> None:
    cur = d
    for k in keys[:-1]:
        if k not in cur or not isinstance(cur[k], dict):
            cur[k] = {}
        cur = cur[k]  # type: ignore[assignment]
    cur[keys[-1]] = value


def _coerce_value(s: str) -> Any:
    # bool
    sl = s.strip().lower()
    if sl in {"true", "1", "yes", "y", "on"}:
        return True
    if sl in {"false", "0", "no", "n", "off"}:
        return False
    # int/float
    try:
        if "." in sl:
            return float(sl)
        return int(sl)
    except Exception:
        pass
    # json
    if (sl.startswith("{") and sl.endswith("}")) or (sl.startswith("[") and sl.endswith("]")):
        try:
            return json.loads(s)
        except Exception:
            return s
    return s


@dataclass
class DictProvider:
    name: str = "dict"
    data: Dict[str, Any] = None  # type: ignore[assignment]

    def load(self) -> Dict[str, Any]:
        return dict(self.data or {})


@dataclass
class EnvProvider:
    """Reads EW6_* variables and builds nested dict via '__' separator.

    Example:
      EW6_NOTIFY__TELEGRAM__BOT_TOKEN=...
    becomes:
      {"notify": {"telegram": {"bot_token": ...}}}

    The prefix is stripped and keys are lowercased.
    """

    name: str = "env"
    prefix: str = "EW6_"
    sep: str = "__"

    def load(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for k, v in os.environ.items():
            if not k.startswith(self.prefix):
                continue
            key = k[len(self.prefix):]
            parts = [p.strip().lower() for p in key.split(self.sep) if p.strip()]
            if not parts:
                continue
            _set_nested(out, parts, _coerce_value(v))
        return out


@dataclass
class FileProvider:
    """Reads JSON or TOML (if tomllib available) config file."""

    name: str = "file"
    path: str = ""
    optional: bool = True

    def load(self) -> Dict[str, Any]:
        if not self.path:
            return {}
        if not os.path.exists(self.path):
            if self.optional:
                return {}
            raise FileNotFoundError(self.path)

        with open(self.path, "rb") as f:
            raw = f.read()

        # detect
        p = self.path.lower()
        if p.endswith(".json"):
            return json.loads(raw.decode("utf-8"))

        if p.endswith(".toml"):
            try:
                import tomllib  # py3.11+
            except Exception:
                # minimal fallback: allow empty
                raise RuntimeError("TOML config requires tomllib (python>=3.11)")
            return tomllib.loads(raw.decode("utf-8"))

        # try json then toml
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            try:
                import tomllib
                return tomllib.loads(raw.decode("utf-8"))
            except Exception as e:
                raise RuntimeError(f"Unsupported config format: {self.path}") from e


@dataclass
class DBProvider:
    """Stub DB provider (V2).

    Intended usage:
      - connect to DB (sqlite/postgres/redis)
      - read config rows by namespace
      - optionally refresh on interval / watch notifications

    In M1 we keep it as a placeholder so imports and composition work.
    """

    name: str = "db"
    dsn: str = ""
    namespace: str = "ew6"
    enabled: bool = False

    def load(self) -> Dict[str, Any]:
        if not self.enabled:
            return {}
        raise NotImplementedError("DBProvider is V2. Enable and implement per target DB.")


@dataclass
class ConfigManager:
    """Compose providers in precedence order (later overrides earlier)."""

    providers: List[ConfigProvider]

    def load(self) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        for p in self.providers:
            payload = p.load()
            if payload:
                _deep_merge(merged, payload)
        return merged
