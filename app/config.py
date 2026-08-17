import os
from dotenv import load_dotenv

load_dotenv()

BUSINESS_NAME = os.getenv("BUSINESS_NAME", "Nexus CCTV & Security Ltd")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./inbox_agent.db")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")

# Where a human salesperson should be "notified" when a lead is captured.
# In this simple version we just log + write to notifications.log.
# Swap in real SMTP / Slack webhook / WhatsApp send in app/notify.py.
SALES_NOTIFY_EMAIL = os.getenv("SALES_NOTIFY_EMAIL", "sales@example.com")

# WhatsApp Cloud API (Meta) - only needed if you wire up the real webhook
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "change-me")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
