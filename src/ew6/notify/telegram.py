from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from typing import List
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from ew6.notify.base import NotificationMessage, Notifier

def _chunks(text: str, max_len: int = 3500) -> List[str]:
    if len(text) <= max_len:
        return [text]
    out = []
    i = 0
    while i < len(text):
        out.append(text[i:i+max_len])
        i += max_len
    return out

def _multipart_form(fields: dict, file_field: str, file_path: str) -> tuple[bytes, str]:
    boundary = "----ew6-" + uuid.uuid4().hex
    lines: List[bytes] = []

    def add_line(s: str) -> None:
        lines.append(s.encode("utf-8"))

    for k, v in fields.items():
        add_line(f"--{boundary}\r\n")
        add_line(f'Content-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n')

    filename = os.path.basename(file_path)
    add_line(f"--{boundary}\r\n")
    add_line(f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n')
    add_line("Content-Type: application/octet-stream\r\n\r\n")
    with open(file_path, "rb") as f:
        lines.append(f.read())
    add_line("\r\n")
    add_line(f"--{boundary}--\r\n")
    body = b"".join(lines)
    return body, boundary

@dataclass(frozen=True)
class TelegramConfig:
    token: str
    chat_id: str
    timeout_s: float = 20.0

class TelegramBotNotifier(Notifier):
    name = "telegram"

    def __init__(self, cfg: TelegramConfig):
        self.cfg = cfg

    @classmethod
    def from_env(cls) -> "TelegramBotNotifier":
        token = os.getenv("EW6_TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.getenv("EW6_TELEGRAM_CHAT_ID", "").strip()
        timeout_s = float(os.getenv("EW6_TELEGRAM_TIMEOUT_S", "20").strip() or "20")
        if not token or not chat_id:
            raise RuntimeError("Missing EW6_TELEGRAM_BOT_TOKEN or EW6_TELEGRAM_CHAT_ID")
        return cls(TelegramConfig(token=token, chat_id=chat_id, timeout_s=timeout_s))

    def _api_url(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self.cfg.token}/{method}"

    def _post_json(self, method: str, payload: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        req = Request(self._api_url(method), data=data, headers={"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=self.cfg.timeout_s) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                return json.loads(raw) if raw else {}
        except HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
            raise RuntimeError(f"Telegram HTTP {e.code}: {body}") from e

    def _post_multipart(self, method: str, fields: dict, file_field: str, file_path: str) -> dict:
        body, boundary = _multipart_form(fields, file_field, file_path)
        req = Request(self._api_url(method), data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        try:
            with urlopen(req, timeout=self.cfg.timeout_s) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                return json.loads(raw) if raw else {}
        except HTTPError as e:
            body2 = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
            raise RuntimeError(f"Telegram HTTP {e.code}: {body2}") from e

    def send(self, msg: NotificationMessage) -> None:
        header = msg.title.strip()
        text = msg.text.strip()
        payload_text = f"{header}\n\n{text}" if header else text
        for part in _chunks(payload_text):
            self._post_json("sendMessage", {"chat_id": self.cfg.chat_id, "text": part})

        for p in msg.attachments or []:
            self._post_multipart("sendDocument", fields={"chat_id": self.cfg.chat_id, "caption": header[:512]},
                                 file_field="document", file_path=p)
