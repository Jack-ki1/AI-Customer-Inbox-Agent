"""
notify.py
---------
"salesperson notification" step of the advanced pipeline:

    lead detected -> CRM record -> [salesperson notification]

This ships as a simple, always-works stub: it appends to notifications.log
and prints to stdout. Swap `notify_salesperson()` internals for a real
integration when you're ready:

    - Email:    smtplib / SendGrid / SES using config.SALES_NOTIFY_EMAIL
    - Slack:    POST to a Slack Incoming Webhook URL
    - WhatsApp: POST to the WhatsApp Cloud API (see app/whatsapp.py pattern)

Keeping this isolated in one file means the rest of the app never needs to
change when you pick a real channel.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from . import config

LOG_PATH = Path(__file__).resolve().parent.parent / "notifications.log"


def notify_salesperson(lead_summary: str) -> None:
    line = f"[{dt.datetime.utcnow().isoformat()}Z] NEW LEAD -> {config.SALES_NOTIFY_EMAIL}\n{lead_summary}\n\n"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line)

    # --- Real email example (uncomment and configure SMTP_* in .env) -----
    # import smtplib, os
    # from email.mime.text import MIMEText
    # msg = MIMEText(lead_summary)
    # msg["Subject"] = "New lead captured by AI Inbox Agent"
    # msg["From"] = os.getenv("SMTP_FROM")
    # msg["To"] = config.SALES_NOTIFY_EMAIL
    # with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT", 587))) as s:
    #     s.starttls()
    #     s.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
    #     s.send_message(msg)
