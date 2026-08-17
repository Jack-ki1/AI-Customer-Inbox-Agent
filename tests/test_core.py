"""
Runs the whole Trigger -> Agent -> Tool -> Action -> Record pipeline with a
fake LLM (no API key required) so we can verify the plumbing - conversation
history, retrieval grounding, lead capture, and DB persistence - actually
works, independent of which real LLM provider is configured.

Run with:  pytest tests/test_core.py -v
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["DATABASE_URL"] = "sqlite:///./test_inbox_agent.db"

from app.agent import InboxAgent  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402


class FakeLLM:
    """Stands in for LLMClient. Deterministic, offline, provider-agnostic."""

    def chat_with_tools(self, system, messages, tools, force_tool=None, **kw):
        text = messages[-1]["content"].lower()
        if "quote" in text or "price" in text or "how much" in text or "install" in text:
            return {
                "tool_calls": [
                    {
                        "name": "classify_message",
                        "arguments": {
                            "intent": "quote_request",
                            "is_lead": True,
                            "urgency": "normal",
                            "lead_summary": "Customer wants a quote / installation.",
                        },
                    }
                ],
                "text": "",
            }
        return {
            "tool_calls": [
                {
                    "name": "classify_message",
                    "arguments": {
                        "intent": "faq",
                        "is_lead": False,
                        "urgency": "low",
                        "lead_summary": "",
                    },
                }
            ],
            "text": "",
        }

    def chat(self, system, messages, **kw):
        # Prove the retrieved context actually reached the prompt.
        assert "CONTEXT:" in system
        return "Yes, we install CCTV in Rongai. Would you like a free site assessment?"


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_faq_flow_no_lead():
    db = SessionLocal()
    agent = InboxAgent(llm=FakeLLM())
    result = agent.handle_message(db, customer_ref="+254700111222", channel="web", message="Are you open on Sunday?")
    assert result["intent"] == "faq"
    assert result["lead_captured"] is False
    assert result["conversation_id"] > 0
    db.close()


def test_quote_request_creates_lead_record():
    db = SessionLocal()
    agent = InboxAgent(llm=FakeLLM())
    result = agent.handle_message(
        db, customer_ref="+254700333444", channel="whatsapp", message="Do you install CCTV in Rongai? How much?"
    )
    assert result["intent"] == "quote_request"
    assert result["lead_captured"] is True
    assert "Rongai" in result["reply"]

    from app.models import Lead

    leads = db.query(Lead).filter(Lead.customer_ref == "+254700333444").all()
    assert len(leads) == 1
    assert leads[0].status == "new"
    db.close()


def test_conversation_history_persists_across_turns():
    db = SessionLocal()
    agent = InboxAgent(llm=FakeLLM())
    ref = "+254700555666"
    r1 = agent.handle_message(db, customer_ref=ref, channel="web", message="Hi there")
    r2 = agent.handle_message(db, customer_ref=ref, channel="web", message="Are you open on Sunday?")
    assert r1["conversation_id"] == r2["conversation_id"]

    from app.models import Message

    msgs = db.query(Message).filter(Message.conversation_id == r1["conversation_id"]).all()
    assert len(msgs) == 4  # 2 user + 2 assistant
    db.close()


def teardown_module(module):
    db_file = Path("./test_inbox_agent.db")
    if db_file.exists():
        db_file.unlink()
