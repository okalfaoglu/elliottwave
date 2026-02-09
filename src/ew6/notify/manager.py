from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import List, Tuple

from ew6.notify.base import NotificationMessage, Notifier
from ew6.notify.telegram import TelegramBotNotifier
from ew6.notify.email import EmailNotifier

def _parse_channels(ch: str) -> List[str]:
    return [c.strip().lower() for c in ch.split(",") if c.strip()]

@dataclass
class SendResult:
    ok: bool
    sent: List[str]
    failed: List[Tuple[str, str]]

class NotifierManager:
    def __init__(self, notifiers: List[Notifier]):
        self.notifiers = notifiers

    @classmethod
    def from_env(cls, channels: str) -> "NotifierManager":
        chs = _parse_channels(channels)
        notifiers: List[Notifier] = []
        for c in chs:
            try:
                if c in ("telegram","tg"):
                    notifiers.append(TelegramBotNotifier.from_env())
                elif c in ("email","mail"):
                    notifiers.append(EmailNotifier.from_env())
                else:
                    print(f"Unknown notify channel (supported: telegram,email): {c}", file=sys.stderr)
            except Exception as e:
                print(f"Notify channel '{c}' disabled: {e}", file=sys.stderr)
        return cls(notifiers)

    def send(self, msg: NotificationMessage, strict: bool=False) -> SendResult:
        if not self.notifiers:
            if strict:
                raise RuntimeError("No notifiers configured")
            return SendResult(ok=False, sent=[], failed=[("all","no notifiers configured")])

        sent: List[str] = []
        failed: List[Tuple[str, str]] = []
        for n in self.notifiers:
            try:
                n.send(msg)
                sent.append(getattr(n, "name", n.__class__.__name__))
            except Exception as e:
                failed.append((getattr(n,"name", n.__class__.__name__), str(e)))
                if strict:
                    raise
        return SendResult(ok=(len(failed)==0), sent=sent, failed=failed)
