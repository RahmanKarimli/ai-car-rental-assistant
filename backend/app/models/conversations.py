import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Text, Integer, BigInteger, Boolean, DateTime, Date, Numeric, ForeignKey, UniqueConstraint, CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSTZRANGE, TSVECTOR, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.db.base import Base, Record

class Conversation(Record, Base):
    __tablename__ = "conversations"
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"), index=True)
    language: Mapped[str] = mapped_column(String(2), default="en")
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    contact_name: Mapped[str | None] = mapped_column(Text)
    contact_email: Mapped[str | None] = mapped_column(Text)
    contact_phone: Mapped[str | None] = mapped_column(Text)
    session_state: Mapped[dict] = mapped_column(JSONB, default=dict)
    state_version: Mapped[int] = mapped_column(default=0)
    active_draft_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("booking_drafts.id", use_alter=True, name="fk_conversation_draft"))
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    retention_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
class ChatLog(Record, Base):
    __tablename__ = "chat_logs"
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id"), index=True)
    sequence: Mapped[int] = mapped_column(BigInteger)
    client_event_id: Mapped[uuid.UUID | None] = mapped_column()
    role: Mapped[str] = mapped_column(String(20))
    raw_content: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agent_runs.id", use_alter=True, name="fk_chat_run"))
    __table_args__ = (UniqueConstraint("conversation_id", "sequence"), UniqueConstraint("conversation_id", "client_event_id"))
class AgentRun(Record, Base):
    __tablename__ = "agent_runs"
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id"))
    client_event_id: Mapped[uuid.UUID] = mapped_column()
    input_log_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_logs.id"))
    event_kind: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="RUNNING")
    checkpoint_id: Mapped[str | None] = mapped_column(Text)
    response_log_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("chat_logs.id"))
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    error_code: Mapped[str | None] = mapped_column(String(80))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("conversation_id", "client_event_id"),)
