from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "warn": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
    "fatal": logging.CRITICAL,
}

@dataclass(frozen=True)
class LogConfig:
    level: str = "info"
    json: bool = False
    to_file: Optional[str] = None
    utc: bool = True

class _JsonFormatter(logging.Formatter):
    def __init__(self, utc: bool = True):
        super().__init__()
        self.utc = utc

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc if self.utc else None)
        payload: Dict[str, Any] = {
            "ts": ts.isoformat(),
            "level": record.levelname.lower(),
            "name": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        for k, v in record.__dict__.items():
            if k.startswith("_") or k in payload:
                continue
            if k in ("args","msg","levelname","levelno","name","created","msecs","relativeCreated",
                     "pathname","filename","module","lineno","funcName","stack_info","exc_info","exc_text",
                     "thread","threadName","processName","process"):
                continue
            payload[k] = v
        return json.dumps(payload, ensure_ascii=False)

def setup_logging(cfg: LogConfig) -> None:
    lvl = _LEVELS.get(cfg.level.lower().strip(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(lvl)
    for h in list(root.handlers):
        root.removeHandler(h)

    if cfg.json:
        fmt = _JsonFormatter(utc=cfg.utc)
    else:
        fmt = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    sh = logging.StreamHandler()
    sh.setLevel(lvl)
    sh.setFormatter(fmt)
    root.addHandler(sh)

    if cfg.to_file:
        os.makedirs(os.path.dirname(cfg.to_file) or ".", exist_ok=True)
        fh = logging.FileHandler(cfg.to_file, encoding="utf-8")
        fh.setLevel(lvl)
        fh.setFormatter(fmt)
        root.addHandler(fh)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
