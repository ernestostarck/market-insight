from collections.abc import Iterable
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.adjudicacion_analytics import (
    AdjudicacionAnalyticsSnapshotRecord,
)
from app.domain.ports.adjudicacion_analytics_repository import (
    AdjudicacionAnalyticsRepository,
)
from app.models.adjudicacion_analytics_snapshot import AdjudicacionAnalyticsSnapshot


class SqlAlchemyAdjudicacionAnalyticsRepository(AdjudicacionAnalyticsRepository):
    """SQLAlchemy repository for adjudicaciones analytics snapshots."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add_many(
        self, entities: list[AdjudicacionAnalyticsSnapshotRecord]
    ) -> list[AdjudicacionAnalyticsSnapshotRecord]:
        models = [
            AdjudicacionAnalyticsSnapshot(
                external_id=entity.external_id,
                snapshot_date=entity.snapshot_date,
                scored_at=entity.scored_at,
                opportunity_score=entity.opportunity_score,
                risk_level=entity.risk_level,
                is_outlier=entity.is_outlier,
                reasons=entity.reasons,
                award_ratio=entity.award_ratio,
                awarded_amount=entity.awarded_amount,
                quality_flags=entity.quality_flags or [],
                source_filters=entity.source_filters or {},
            )
            for entity in entities
        ]
        self._session.add_all(models)
        self._session.commit()
        for model in models:
            self._session.refresh(model)
        return [self._to_record(model) for model in models]

    def list_by_external_id(
        self, external_id: str, limit: int = 50
    ) -> Iterable[AdjudicacionAnalyticsSnapshotRecord]:
        models = self._session.scalars(
            select(AdjudicacionAnalyticsSnapshot)
            .where(AdjudicacionAnalyticsSnapshot.external_id == external_id)
            .order_by(AdjudicacionAnalyticsSnapshot.scored_at.desc())
            .limit(limit)
        ).all()
        return [self._to_record(model) for model in models]

    def get_latest(
        self, external_id: str
    ) -> AdjudicacionAnalyticsSnapshotRecord | None:
        model = self._session.scalars(
            select(AdjudicacionAnalyticsSnapshot)
            .where(AdjudicacionAnalyticsSnapshot.external_id == external_id)
            .order_by(AdjudicacionAnalyticsSnapshot.scored_at.desc())
            .limit(1)
        ).first()
        return self._to_record(model) if model is not None else None

    def list_by_snapshot_date(
        self, snapshot_date: date
    ) -> Iterable[AdjudicacionAnalyticsSnapshotRecord]:
        models = self._session.scalars(
            select(AdjudicacionAnalyticsSnapshot)
            .where(AdjudicacionAnalyticsSnapshot.snapshot_date == snapshot_date)
            .order_by(AdjudicacionAnalyticsSnapshot.opportunity_score.desc())
        ).all()
        return [self._to_record(model) for model in models]

    def list_by_date_range(
        self,
        start_date: date,
        end_date: date,
    ) -> Iterable[AdjudicacionAnalyticsSnapshotRecord]:
        models = self._session.scalars(
            select(AdjudicacionAnalyticsSnapshot)
            .where(AdjudicacionAnalyticsSnapshot.snapshot_date >= start_date)
            .where(AdjudicacionAnalyticsSnapshot.snapshot_date <= end_date)
            .order_by(AdjudicacionAnalyticsSnapshot.snapshot_date.asc())
            .order_by(AdjudicacionAnalyticsSnapshot.scored_at.asc())
        ).all()
        return [self._to_record(model) for model in models]

    @staticmethod
    def _to_record(
        model: AdjudicacionAnalyticsSnapshot | None,
    ) -> AdjudicacionAnalyticsSnapshotRecord:
        if model is None:
            raise ValueError("Adjudicacion analytics model is required")
        return AdjudicacionAnalyticsSnapshotRecord(
            id=model.id,
            external_id=model.external_id,
            snapshot_date=model.snapshot_date,
            scored_at=model.scored_at,
            opportunity_score=model.opportunity_score,
            risk_level=model.risk_level,
            is_outlier=model.is_outlier,
            reasons=model.reasons,
            award_ratio=model.award_ratio,
            awarded_amount=model.awarded_amount,
            quality_flags=model.quality_flags,
            source_filters=model.source_filters,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
