import datetime as dt

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    channel = Column(String, default="web")  # web | whatsapp | email
    customer_ref = Column(String, index=True)  # phone number / email / session id
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(String)  # user | assistant
    content = Column(Text)
    intent = Column(String, nullable=True)  # detected intent, for analytics
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


class Lead(Base):
    """A captured sales opportunity - the CRM record + trigger for salesperson notification."""

    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    customer_ref = Column(String)
    name = Column(String, nullable=True)
    interest = Column(Text)  # what they want / asked about
    urgency = Column(String, default="normal")  # low | normal | high
    status = Column(String, default="new")  # new | contacted | won | lost
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    conversation = relationship("Conversation", back_populates="leads")
