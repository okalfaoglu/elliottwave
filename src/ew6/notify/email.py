from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import List

from ew6.notify.base import NotificationMessage, Notifier

@dataclass(frozen=True)
class EmailConfig:
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    starttls: bool = True
    mail_from: str = ""
    mail_to: List[str] = None  # type: ignore

class EmailNotifier(Notifier):
    name = "email"

    def __init__(self, cfg: EmailConfig):
        if not cfg.mail_to:
            raise ValueError("EmailConfig.mail_to must not be empty")
        self.cfg = cfg

    @classmethod
    def from_env(cls) -> "EmailNotifier":
        host = os.getenv("EW6_SMTP_HOST", "").strip()
        port = int(os.getenv("EW6_SMTP_PORT", "587").strip() or "587")
        user = os.getenv("EW6_SMTP_USER", "").strip()
        password = os.getenv("EW6_SMTP_PASSWORD", "").strip()
        starttls = os.getenv("EW6_SMTP_STARTTLS", "1").strip() not in ("0","false","False","no","NO")
        mail_from = os.getenv("EW6_EMAIL_FROM", user).strip()
        to_raw = os.getenv("EW6_EMAIL_TO", "").strip()
        mail_to = [x.strip() for x in to_raw.split(",") if x.strip()]
        if not host or not mail_from or not mail_to:
            raise RuntimeError("Missing EW6_SMTP_HOST / EW6_EMAIL_FROM / EW6_EMAIL_TO (and optionally EW6_SMTP_USER/PASSWORD)")
        return cls(EmailConfig(
            smtp_host=host, smtp_port=port, smtp_user=user, smtp_password=password,
            starttls=starttls, mail_from=mail_from, mail_to=mail_to,
        ))

    def send(self, msg: NotificationMessage) -> None:
        em = EmailMessage()
        em["Subject"] = msg.title
        em["From"] = self.cfg.mail_from
        em["To"] = ", ".join(self.cfg.mail_to)
        em.set_content(msg.text)

        for p in msg.attachments or []:
            try:
                with open(p, "rb") as f:
                    data = f.read()
                em.add_attachment(data, maintype="application", subtype="octet-stream", filename=os.path.basename(p))
            except FileNotFoundError:
                continue

        with smtplib.SMTP(self.cfg.smtp_host, self.cfg.smtp_port, timeout=20) as s:
            if self.cfg.starttls:
                s.starttls()
            if self.cfg.smtp_user:
                s.login(self.cfg.smtp_user, self.cfg.smtp_password)
            s.send_message(em)
