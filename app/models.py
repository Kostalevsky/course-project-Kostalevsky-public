import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


def generate_uuid():
    return str(uuid.uuid4())


class Deck(Base):

    __tablename__ = "decks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    cards = relationship("Card", back_populates="deck", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "cards": len(self.cards) if self.cards else 0,
        }


class Card(Base):

    __tablename__ = "cards"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    deck_id = Column(String(36), ForeignKey("decks.id", ondelete="CASCADE"), nullable=False)
    front = Column(String(200), nullable=False)
    back = Column(String(500), nullable=False)
    hint = Column(String(200), nullable=True)
    image_path = Column(String(255), nullable=True)

    due_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    interval_days = Column(Integer, default=0, nullable=False)
    ease = Column(Float, default=2.5, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    deck = relationship("Deck", back_populates="cards")

    def to_dict(self):
        return {
            "id": self.id,
            "deck_id": self.deck_id,
            "front": self.front,
            "back": self.back,
            "hint": self.hint,
            "due_at": self.due_at,
            "interval_days": self.interval_days,
            "ease": self.ease,
        }
