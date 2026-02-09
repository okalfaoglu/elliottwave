from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List

@dataclass
class NotificationMessage:
    title: str
    text: str
    level: str = "info"
    attachments: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

class Notifier:
    name: str = "notifier"
    def send(self, msg: NotificationMessage) -> None:  # pragma: no cover
        raise NotImplementedError
