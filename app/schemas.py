from pydantic import BaseModel


class ChatRequest(BaseModel):
    customer_ref: str  # phone number, email, or session id - identifies the customer
    message: str
    channel: str = "web"  # web | whatsapp | email


class ChatResponse(BaseModel):
    reply: str
    intent: str
    lead_captured: bool
    conversation_id: int
