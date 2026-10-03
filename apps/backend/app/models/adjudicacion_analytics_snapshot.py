from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AdjudicacionAnalyticsSnapshot(Base):
    __tablename__ = "adjudicacion_analytics_snapshots"
    __table_args__ = {"schema": "analytics"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    external_id: Mapped[str] = mapped_column(String(128), index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    opportunity_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), index=True)
    is_outlier: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    award_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    awarded_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_flags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    source_filters: Mapped[dict[str, str]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
