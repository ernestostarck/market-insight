from __future__ import annotations

from datetime import datetime
from statistics import mean, median, pstdev
from typing import Any

from app.integrations.chilecompra.exceptions import ChileCompraValidationError
from app.integrations.chilecompra.models import (
    AdjudicacionAnalyticInsight,
    AdjudicacionAPIItem,
    AdjudicacionesAnalyticsResult,
    AdjudicacionesAnalyticsSummary,
    AdjudicacionesAPIResponse,
    AdjudicacionesScoringConfig,
    NormalizedAdjudicacion,
)

_FALLBACK_SOURCE_FLAG = "fallback_payload_from_licitaciones"
_FALLBACK_PARTIAL_FIELDS_FLAG = "fallback_partial_adjudicacion_fields"
_FALLBACK_SOURCE_RESOURCE = "licitaciones.json"


def parse_adjudicaciones_payload(
    payload: dict[str, Any] | list[Any],
) -> AdjudicacionesAPIResponse:
    if isinstance(payload, list):
        payload = {"Cantidad": len(payload), "Listado": payload}
    if not isinstance(payload, dict):
        raise ChileCompraValidationError(
            "Adjudicaciones payload must be an object or list"
        )

    if (
        "Listado" in payload
        and "Cantidad" not in payload
        and isinstance(payload["Listado"], list)
    ):
        payload = {**payload, "Cantidad": len(payload["Listado"])}

    return AdjudicacionesAPIResponse.model_validate(payload)


def normalize_adjudicaciones(
    payload: dict[str, Any] | list[Any],
) -> list[NormalizedAdjudicacion]:
    parsed = parse_adjudicaciones_payload(payload)
    return [_normalize_adjudicacion(item) for item in parsed.listado]


def analyze_adjudicaciones(
    payload: dict[str, Any] | list[Any],
    config: AdjudicacionesScoringConfig | None = None,
) -> AdjudicacionesAnalyticsResult:
    normalized_items = normalize_adjudicaciones(payload)
    scoring_config = config or AdjudicacionesScoringConfig()

    awarded_amounts = [
        item.awarded_amount
        for item in normalized_items
        if item.awarded_amount is not None
    ]
    award_ratios = [
        item.award_ratio for item in normalized_items if item.award_ratio is not None
    ]

    amount_std = pstdev(awarded_amounts) if len(awarded_amounts) >= 2 else 0.0
    amount_mean = mean(awarded_amounts) if awarded_amounts else None

    insights: list[AdjudicacionAnalyticInsight] = []
    risk_distribution = {"low": 0, "medium": 0, "high": 0}
    total_score = 0.0

    for item in normalized_items:
        score, risk, reasons, is_outlier = _score_item(
            item,
            scoring_config,
            amount_mean=amount_mean,
            amount_std=amount_std,
        )
        risk_distribution[risk] += 1
        total_score += score

        insights.append(
            AdjudicacionAnalyticInsight(
                external_id=item.external_id,
                opportunity_score=score,
                risk_level=risk,
                is_outlier=is_outlier,
                reasons=reasons,
                award_ratio=item.award_ratio,
                awarded_amount=item.awarded_amount,
                quality_flags=item.quality_flags,
            )
        )

    summary = AdjudicacionesAnalyticsSummary(
        total_items=len(normalized_items),
        scored_items=len(insights),
        outlier_items=sum(1 for item in insights if item.is_outlier),
        avg_opportunity_score=round(total_score / len(insights), 2)
        if insights
        else None,
        median_award_ratio=round(median(award_ratios), 4) if award_ratios else None,
        risk_distribution=risk_distribution,
    )
    return AdjudicacionesAnalyticsResult(summary=summary, items=insights)


def _normalize_adjudicacion(item: AdjudicacionAPIItem) -> NormalizedAdjudicacion:
    raw_payload = item.model_dump(by_alias=True)
    external_id = item.codigo_adjudicacion or item.codigo or item.codigo_externo or ""
    if not external_id:
        raise ChileCompraValidationError("Adjudicacion sin codigo externo")

    awarded_amount = _to_float(item.monto_adjudicado)
    estimated_amount = _to_float(item.monto_estimado)
    award_ratio = None
    if awarded_amount is not None and estimated_amount and estimated_amount > 0:
        award_ratio = round(awarded_amount / estimated_amount, 4)

    offers_count = _to_int(item.cantidad_ofertas)

    quality_flags: list[str] = []
    is_fallback_payload = (
        raw_payload.get("__source_resource") == _FALLBACK_SOURCE_RESOURCE
    )
    if is_fallback_payload:
        quality_flags.append(_FALLBACK_SOURCE_FLAG)

    if awarded_amount is None:
        quality_flags.append("missing_awarded_amount")
    if estimated_amount is None:
        quality_flags.append("missing_estimated_amount")
    if offers_count is None:
        quality_flags.append("missing_offers_count")
    if not item.nombre:
        quality_flags.append("missing_title")
    if is_fallback_payload and any(
        flag in quality_flags
        for flag in (
            "missing_awarded_amount",
            "missing_estimated_amount",
            "missing_offers_count",
        )
    ):
        quality_flags.append(_FALLBACK_PARTIAL_FIELDS_FLAG)

    status_value = item.estado or str(item.codigo_estado or "UNKNOWN")
    return NormalizedAdjudicacion(
        external_id=external_id,
        title=item.nombre or external_id,
        status=status_value.strip().upper(),
        published_at=_parse_datetime(item.fecha_publicacion),
        awarded_at=_parse_datetime(item.fecha_adjudicacion),
        agency_code=item.codigo_organismo,
        agency_name=item.nombre_organismo,
        provider_code=item.codigo_proveedor,
        provider_name=item.nombre_proveedor,
        awarded_amount=awarded_amount,
        estimated_amount=estimated_amount,
        award_ratio=award_ratio,
        offers_count=offers_count,
        quality_flags=quality_flags,
        raw_payload=raw_payload,
    )


def _score_item(
    item: NormalizedAdjudicacion,
    config: AdjudicacionesScoringConfig,
    amount_mean: float | None,
    amount_std: float,
) -> tuple[float, str, list[str], bool]:
    reasons: list[str] = []

    ratio_component = _ratio_score(item.award_ratio)
    competition_component = _competition_score(item.offers_count)
    quality_penalty = _quality_penalty(
        len(item.quality_flags), config.max_quality_flags_for_penalty
    )

    score = ratio_component * 0.55 + competition_component * 0.35 - quality_penalty

    is_outlier = False
    if item.award_ratio is not None:
        if item.award_ratio > config.ratio_outlier_upper:
            is_outlier = True
            reasons.append("high_award_ratio")
        elif item.award_ratio < config.ratio_outlier_lower:
            is_outlier = True
            reasons.append("low_award_ratio")

    if amount_mean is not None and amount_std > 0 and item.awarded_amount is not None:
        zscore = abs((item.awarded_amount - amount_mean) / amount_std)
        if zscore >= config.amount_zscore_threshold:
            is_outlier = True
            reasons.append("awarded_amount_outlier")

    if item.quality_flags:
        reasons.append("data_quality_issues")
    if _FALLBACK_SOURCE_FLAG in item.quality_flags:
        reasons.append("fallback_source_data")

    if is_outlier:
        score -= 15

    score = max(0.0, min(100.0, round(score, 2)))

    if score >= 70:
        risk = "low"
    elif score >= 45:
        risk = "medium"
    else:
        risk = "high"

    return score, risk, reasons, is_outlier


def _ratio_score(award_ratio: float | None) -> float:
    if award_ratio is None:
        return 50.0
    if award_ratio <= 0.6:
        return 95.0
    if award_ratio <= 0.8:
        return 85.0
    if award_ratio <= 1.0:
        return 70.0
    if award_ratio <= 1.2:
        return 50.0
    return 25.0


def _competition_score(offers_count: int | None) -> float:
    if offers_count is None:
        return 45.0
    if offers_count <= 2:
        return 55.0
    if offers_count <= 5:
        return 75.0
    if offers_count <= 9:
        return 85.0
    return 65.0


def _quality_penalty(flag_count: int, max_flags_for_penalty: int) -> float:
    bounded = min(flag_count, max_flags_for_penalty)
    return bounded * 6.0


def _to_float(value: float | str | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, float):
        return value

    candidate = value.strip().replace("$", "").replace(" ", "")
    if "," in candidate and "." in candidate:
        candidate = candidate.replace(".", "").replace(",", ".")
    elif "," in candidate:
        candidate = candidate.replace(",", ".")

    try:
        return float(candidate)
    except ValueError:
        return None


def _to_int(value: int | str | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    candidate = value.strip()
    if not candidate:
        return None
    try:
        return int(candidate)
    except ValueError:
        return None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    candidate = value.strip()
    for fmt in (
        "%d%m%Y",
        "%Y%m%d",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            return datetime.strptime(candidate, fmt)
        except ValueError:
            continue
    return None
