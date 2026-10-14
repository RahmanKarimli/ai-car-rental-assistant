import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Text, Integer, BigInteger, Boolean, DateTime, Date, Numeric, ForeignKey, UniqueConstraint, CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSTZRANGE, TSVECTOR, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.db.base import Base, Record

class PolicyDocument(Record, Base):
    __tablename__ = "policy_documents"
    document_key: Mapped[str] = mapped_column(Text)
    topic: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(2))
    version: Mapped[int] = mapped_column()
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id"))
    source_asset_key: Mapped[str] = mapped_column(Text)
    full_text: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("admin_users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("document_key", "language", "version"),)
class PolicyChunk(Record, Base):
    __tablename__ = "policy_chunks"
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("policy_documents.id"))
    chunk_index: Mapped[int] = mapped_column()
    content: Mapped[str] = mapped_column(Text)
    section_reference: Mapped[str] = mapped_column(Text)
    search_vector = mapped_column(TSVECTOR, nullable=False)
    embedding = mapped_column(Vector(1536), nullable=False)
    embedding_model: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    __table_args__ = (Index("policy_search", "search_vector", postgresql_using="gin"), Index("policy_embedding", "embedding", postgresql_using="hnsw", postgresql_ops={"embedding":"vector_cosine_ops"}))
