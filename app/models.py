from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

from sqlalchemy import Boolean, DateTime, Float, Integer, String


class ProductMetadata(Base):
    __tablename__ = "product_metadata"

    article_number: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    url: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class PriceObservation(Base):
    __tablename__ = "price_observations"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    article_number: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )

    price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

class SeenSecondHandOffer(Base):
    __tablename__ = "seen_second_hand_offers"

    offer_uuid: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )

    article_number: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )

    store_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

class SecondHandOfferRecord(Base):
    __tablename__ = "second_hand_offers"

    offer_uuid: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )

    article_number: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )

    store_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )

    store_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    original_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    condition_code: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    condition_title: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    reason_discount: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    additional_info: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )