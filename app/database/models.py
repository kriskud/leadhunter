from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, LeadStatus


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus, name="lead_status", native_enum=False),
        default=LeadStatus.NEW,
        nullable=False,
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    enrichment: Mapped["EnrichmentData | None"] = relationship(
        back_populates="lead", uselist=False, cascade="all, delete-orphan"
    )
    qualification: Mapped["Qualification | None"] = relationship(
        back_populates="lead", uselist=False, cascade="all, delete-orphan"
    )
    message_drafts: Mapped[list["MessageDraft"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan"
    )


class EnrichmentData(Base):
    __tablename__ = "enrichment_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    page_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    page_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    emails: Mapped[str | None] = mapped_column(Text, nullable=True)
    phones: Mapped[str | None] = mapped_column(Text, nullable=True)
    social_links: Mapped[str | None] = mapped_column(Text, nullable=True)
    booking_links: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    lead: Mapped["Lead"] = relationship(back_populates="enrichment")


class Qualification(Base):
    __tablename__ = "qualifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    is_private_practice: Mapped[bool | None] = mapped_column(nullable=True)
    estimated_staff_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_online_booking: Mapped[bool | None] = mapped_column(nullable=True)
    booking_provider: Mapped[str | None] = mapped_column(String(128), nullable=True)
    has_crm: Mapped[bool | None] = mapped_column(nullable=True)
    business_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    lead: Mapped["Lead"] = relationship(back_populates="qualification")


class MessageDraft(Base):
    __tablename__ = "message_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    lead: Mapped["Lead"] = relationship(back_populates="message_drafts")
