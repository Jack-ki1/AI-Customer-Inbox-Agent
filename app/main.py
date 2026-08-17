from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import config
from .agent import InboxAgent
from .database import get_db, init_db
from .models import Lead
from .schemas import ChatRequest, ChatResponse

app = FastAPI(title="AI Customer Inbox Agent", version="1.0.0")

STATIC_DIR = __file__.rsplit("/", 2)[0] + "/static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

_agent: InboxAgent | None = None


@app.on_event("startup")
def startup():
    init_db()
    global _agent
    # LLMClient is constructed lazily/at startup so a missing API key fails
    # fast with a clear error instead of on the first customer message.
    try:
        _agent = InboxAgent()
    except RuntimeError as e:
        print(f"WARNING: LLM client not initialised yet: {e}")
        _agent = None


def get_agent() -> InboxAgent:
    global _agent
    if _agent is None:
        _agent = InboxAgent()  # raises a clear error if API key still missing
    return _agent


@app.get("/")
def demo_ui():
    return FileResponse(STATIC_DIR + "/index.html")


@app.get("/health")
def health():
    return {"status": "ok", "provider": config.LLM_PROVIDER}


# --------------------------------------------------------------------- #
# Channel 1: generic web chat (also used by the demo UI above)
# --------------------------------------------------------------------- #
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db), agent: InboxAgent = Depends(get_agent)):
    result = agent.handle_message(
        db=db, customer_ref=req.customer_ref, channel=req.channel, message=req.message
    )
    return ChatResponse(**result)


# --------------------------------------------------------------------- #
# Channel 2: WhatsApp Cloud API webhook
# Docs: https://developers.facebook.com/docs/whatsapp/cloud-api/guides/set-up-webhooks
# --------------------------------------------------------------------- #
@app.get("/webhook/whatsapp")
def whatsapp_verify(request: Request):
    """Meta calls this once when you register the webhook URL in the dashboard."""
    params = request.query_params
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == config.WHATSAPP_VERIFY_TOKEN
    ):
        return Response(content=params.get("hub.challenge", ""), media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook/whatsapp")
async def whatsapp_receive(
    request: Request, db: Session = Depends(get_db), agent: InboxAgent = Depends(get_agent)
):
    payload = await request.json()
    try:
        entry = payload["entry"][0]["changes"][0]["value"]
        message = entry["messages"][0]
        from_number = message["from"]
        text = message["text"]["body"]
    except (KeyError, IndexError):
        # Status callbacks (delivered/read receipts) land here too - ignore them.
        return JSONResponse({"status": "ignored"})

    result = agent.handle_message(db=db, customer_ref=from_number, channel="whatsapp", message=text)
    _send_whatsapp_message(to=from_number, body=result["reply"])
    return JSONResponse({"status": "ok"})


def _send_whatsapp_message(to: str, body: str) -> None:
    """Send the agent's reply back out via the WhatsApp Cloud API."""
    if not config.WHATSAPP_ACCESS_TOKEN:
        print(f"[whatsapp-stub] would send to {to}: {body}")
        return
    import requests

    url = f"https://graph.facebook.com/v20.0/{config.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {config.WHATSAPP_ACCESS_TOKEN}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    if resp.status_code >= 400:
        print(f"[whatsapp] send failed: {resp.status_code} {resp.text}")


# --------------------------------------------------------------------- #
# Channel 3: Email (simplified). Point a Gmail "forwarding" rule or a small
# poller (see app/gmail_poller.py) at this endpoint, or call it from a cron.
# --------------------------------------------------------------------- #
@app.post("/webhook/email")
def email_receive(
    from_address: str, subject: str, body: str,
    db: Session = Depends(get_db), agent: InboxAgent = Depends(get_agent),
):
    full_message = f"Subject: {subject}\n\n{body}"
    result = agent.handle_message(db=db, customer_ref=from_address, channel="email", message=full_message)
    # Wire up real sending via Gmail API / SMTP in notify.py-style module.
    print(f"[email-stub] would reply to {from_address}: {result['reply']}")
    return result


# --------------------------------------------------------------------- #
# Simple leads view - stands in for "CRM record" visibility
# --------------------------------------------------------------------- #
@app.get("/leads")
def list_leads(db: Session = Depends(get_db)):
    leads = db.query(Lead).order_by(Lead.id.desc()).all()
    return [
        {
            "id": l.id,
            "customer_ref": l.customer_ref,
            "interest": l.interest,
            "urgency": l.urgency,
            "status": l.status,
            "created_at": l.created_at.isoformat(),
        }
        for l in leads
    ]
