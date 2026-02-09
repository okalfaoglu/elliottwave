"""Stubs for WhatsApp / X / Instagram.

These platforms typically require OAuth/app approval and are better done in V2.
We keep placeholders so the rest of the app can depend on a stable interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from ew6.notify.core import Message


@dataclass(frozen=True)
class StubConfig:
    name: str = "stub"


class StubNotifier:
    def __init__(self, cfg: StubConfig):
        self.cfg = cfg

    def send(self, msg: Message) -> None:
        # no-op
        return
