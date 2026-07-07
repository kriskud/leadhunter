import enum

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class LeadStatus(str, enum.Enum):
    NEW = "NEW"
    ENRICHED = "ENRICHED"
    QUALIFIED = "QUALIFIED"
    SCORED = "SCORED"
    MESSAGE_GENERATED = "MESSAGE_GENERATED"
    REJECTED = "REJECTED"
