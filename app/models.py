from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


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