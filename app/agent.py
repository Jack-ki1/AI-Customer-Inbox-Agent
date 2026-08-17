"""
agent.py
--------
Implements the full pipeline from the spec:

    Trigger (channel message)
        -> Agent (this module)
            -> Tool: classify_message (LLM, forced tool call = intent detection
               + lead signal in one structured round trip)
            -> Tool: knowledge_base.search (local TF-IDF retrieval, no LLM)
            -> Action: generate grounded reply (LLM, plain chat)
            -> Action: capture_lead if buying intent detected
        -> Record (Conversation / Message / Lead rows in the database)
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from . import config
from .llm_client import LLMClient
from .models import Conversation, Lead, Message
from .notify import notify_salesperson
from .retrieval import knowledge_base

CLASSIFY_TOOL = {
    "name": "classify_message",
    "description": (
        f"Classify an incoming customer message for {config.BUSINESS_NAME}, "
        "a security systems installation business in Nairobi, Kenya."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": ["faq", "booking_interest", "quote_request", "complaint", "greeting", "other"],
                "description": "The primary intent of the message.",
            },
            "is_lead": {
                "type": "boolean",
                "description": (
                    "True if the customer shows buying intent: asking for pricing, "
                    "wanting installation, wanting a site visit, or similar."
                ),
            },
            "urgency": {"type": "string", "enum": ["low", "normal", "high"]},
            "lead_summary": {
                "type": "string",
                "description": (
                    "One sentence summary of what the customer wants, written for a "
                    "salesperson to act on. Empty string if is_lead is false."
                ),
            },
        },
        "required": ["intent", "is_lead", "urgency", "lead_summary"],
    },
}

SYSTEM_PROMPT_TEMPLATE = """You are the AI customer support agent for {business_name}, \
a security systems company in Nairobi, Kenya.

Rules:
- Answer ONLY using the CONTEXT provided below. If the context does not cover \
the question, say you'll have a team member confirm - never invent prices, \
availability, or policies.
- Be concise and warm, like a helpful staff member replying on WhatsApp. \
2-4 sentences unless the question needs a short list.
- If the customer is asking for pricing or wants to book, end your reply by \
offering to arrange a free site assessment or send a written quotation.
- Never claim to have booked anything - you are only replying to a message here.

CONTEXT:
{context}
"""


class InboxAgent:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def handle_message(
        self, db: Session, customer_ref: str, channel: str, message: str
    ) -> dict:
        conversation = self._get_or_create_conversation(db, customer_ref, channel)

        db.add(Message(conversation_id=conversation.id, role="user", content=message))
        db.commit()

        # --- Step 1: intent detection (forced tool call = structured output) ---
        classification = self._classify(message)
        intent = classification.get("intent", "other")

        # --- Step 2: knowledge retrieval (local, no LLM call) ---
        context = knowledge_base.context_block(message)

        # --- Step 3: response generation, grounded in retrieved context ---
        reply = self._generate_reply(conversation, message, context)

        db.add(
            Message(
                conversation_id=conversation.id, role="assistant", content=reply, intent=intent
            )
        )

        # --- Step 4: lead capture + CRM record + salesperson notification ---
        lead_captured = False
        if classification.get("is_lead"):
            lead = Lead(
                conversation_id=conversation.id,
                customer_ref=customer_ref,
                interest=classification.get("lead_summary") or message,
                urgency=classification.get("urgency", "normal"),
                status="new",
            )
            db.add(lead)
            db.commit()
            db.refresh(lead)
            lead_captured = True
            notify_salesperson(
                f"Customer: {customer_ref} (via {channel})\n"
                f"Interest: {lead.interest}\n"
                f"Urgency: {lead.urgency}\n"
                f"Conversation #{conversation.id}"
            )
        else:
            db.commit()

        return {
            "reply": reply,
            "intent": intent,
            "lead_captured": lead_captured,
            "conversation_id": conversation.id,
        }

    # ------------------------------------------------------------------ #
    def _get_or_create_conversation(self, db: Session, customer_ref: str, channel: str) -> Conversation:
        convo = (
            db.query(Conversation)
            .filter(Conversation.customer_ref == customer_ref, Conversation.channel == channel)
            .order_by(Conversation.id.desc())
            .first()
        )
        if convo:
            return convo
        convo = Conversation(customer_ref=customer_ref, channel=channel)
        db.add(convo)
        db.commit()
        db.refresh(convo)
        return convo

    def _classify(self, message: str) -> dict:
        result = self.llm.chat_with_tools(
            system="You classify customer messages. Always call the classify_message tool.",
            messages=[{"role": "user", "content": message}],
            tools=[CLASSIFY_TOOL],
            force_tool="classify_message",
            temperature=0.0,
            max_tokens=300,
        )
        for call in result["tool_calls"]:
            if call["name"] == "classify_message":
                return call["arguments"]
        # Fallback if a provider returns no tool call for any reason.
        return {"intent": "other", "is_lead": False, "urgency": "normal", "lead_summary": ""}

    def _generate_reply(self, conversation: Conversation, message: str, context: str) -> str:
        system = SYSTEM_PROMPT_TEMPLATE.format(business_name=config.BUSINESS_NAME, context=context)
        history = [
            {"role": m.role, "content": m.content}
            for m in conversation.messages[-6:]  # short rolling window
        ]
        if not history or history[-1]["content"] != message:
            history.append({"role": "user", "content": message})
        return self.llm.chat(system=system, messages=history, temperature=0.3, max_tokens=350)
