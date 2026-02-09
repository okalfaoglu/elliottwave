"""Notification package (M1.11: telegram+email).

Public helper:
  - notify_run(results, ranked, channels, fmt, attachments=None, title=None)

Env defaults:
  - EW6_NOTIFY_CHANNELS=telegram,email
  - EW6_NOTIFY_FORMAT=compact|pretty
  - EW6_NOTIFY_ATTACHMENTS=out/report.json,out/report.csv,out/reco.json,out/trades.csv
"""

from __future__ import annotations

import os
import json
from typing import Any, Dict, List, Optional, Sequence

from ew6.notify.base import NotificationMessage
from ew6.notify.manager import NotifierManager
from ew6.notify.formatter import format_compact, format_pretty


def _parse_csv(s: str) -> List[str]:
    return [x.strip() for x in (s or "").split(",") if x.strip()]


def notify_run(
    *,
    results: Sequence[Dict[str, Any]],
    ranked: Sequence[Dict[str, Any]],
    channels: Optional[Sequence[str]] = None,
    fmt: str = "compact",
    attachments: Optional[Sequence[str]] = None,
    title: Optional[str] = None,
    level: str = "info",
) -> None:
    """Send summary notification to configured channels."""

    ch = list(channels) if channels is not None else _parse_csv(os.getenv("EW6_NOTIFY_CHANNELS", ""))
    if not ch:
        return

    fmt2 = (fmt or os.getenv("EW6_NOTIFY_FORMAT", "compact") or "compact").strip().lower()
    title2 = (title or os.getenv("EW6_NOTIFY_TITLE", "EW6 Report") or "EW6 Report").strip()

    # attachments: caller + env
    att: List[str] = []
    if attachments:
        att += list(attachments)
    att += _parse_csv(os.getenv("EW6_NOTIFY_ATTACHMENTS", ""))
    # keep only existing files
    att2 = [p for p in att if p and os.path.exists(p)]

    if fmt2 == "pretty":
        text = format_pretty(results=list(results), ranked=list(ranked))
    else:
        text = format_compact(results=list(results), ranked=list(ranked))

    msg = NotificationMessage(title=title2, text=text, level=level, attachments=att2, meta={"fmt": fmt2})
    mgr = NotifierManager.from_env(",".join(ch))
    mgr.send(msg, strict=False)


__all__ = ["notify_run"]
