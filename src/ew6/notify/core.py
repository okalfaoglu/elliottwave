from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol


@dataclass(frozen=True)
class Message:
    title: str
    body: str
    fmt: str = "text"  # text|markdown|html
    attachments: Optional[List[str]] = None


class Notifier(Protocol):
    def send(self, msg: Message) -> None: ...


class MultiNotifier:
    def __init__(self, notifiers: List[Notifier]):
        self.notifiers = list(notifiers)

    def send(self, msg: Message) -> None:
        for n in self.notifiers:
            n.send(msg)
