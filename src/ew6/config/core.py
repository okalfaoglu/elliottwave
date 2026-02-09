from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

try:
    import tomllib
except Exception:
    tomllib = None  # type: ignore

def merge_dicts(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in overlay.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = merge_dicts(out[k], v)
        else:
            out[k] = v
    return out

def _parse_scalar(v: str) -> Any:
    s = v.strip()
    if s.lower() in ("true","false"):
        return s.lower() == "true"
    try:
        if s.startswith("0") and len(s) > 1 and s[1].isdigit():
            raise ValueError
        return int(s)
    except Exception:
        pass
    try:
        return float(s)
    except Exception:
        pass
    if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
        try:
            return json.loads(s)
        except Exception:
            pass
    return s

def _env_to_dict(prefix: str="EW6_") -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in os.environ.items():
        if not k.startswith(prefix):
            continue
        key = k[len(prefix):].lower()
        if "__" not in key:
            out[key] = _parse_scalar(v)
            continue
        path = key.split("__")
        cur = out
        for part in path[:-1]:
            cur = cur.setdefault(part, {})  # type: ignore
        cur[path[-1]] = _parse_scalar(v)
    return out

def _load_file(path: str) -> Dict[str, Any]:
    p = path.strip()
    if not p:
        return {}
    with open(p, "rb") as f:
        raw = f.read()
    if p.lower().endswith(".json"):
        return json.loads(raw.decode("utf-8"))
    if p.lower().endswith(".toml"):
        if tomllib is None:
            raise RuntimeError("tomllib not available; requires Python 3.11+ for TOML config")
        return tomllib.loads(raw.decode("utf-8"))
    raise RuntimeError(f"Unsupported config format for {p} (use .toml or .json)")

@dataclass
class Config:
    data: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any=None) -> Any:
        cur: Any = self.data
        for part in key.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.data)

def load_config(*, defaults: Optional[Dict[str, Any]]=None, file_path: Optional[str]=None,
                env_prefix: str="EW6_", overrides: Optional[Dict[str, Any]]=None) -> Config:
    cfg: Dict[str, Any] = defaults or {}
    if file_path:
        cfg = merge_dicts(cfg, _load_file(file_path))
    cfg = merge_dicts(cfg, _env_to_dict(prefix=env_prefix))
    if overrides:
        cfg = merge_dicts(cfg, overrides)
    return Config(cfg)
