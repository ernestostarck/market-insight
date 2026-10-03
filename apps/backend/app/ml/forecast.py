from dataclasses import dataclass
from typing import Iterable

import numpy as np


@dataclass(slots=True)
class PriceForecastResult:
    predicted_price: float
    confidence: float


class PriceForecaster:
    def forecast(self, historical_prices: Iterable[float]) -> PriceForecastResult:
        values = np.array(list(historical_prices), dtype=float)
        if values.size == 0:
            return PriceForecastResult(predicted_price=0.0, confidence=0.0)
        return PriceForecastResult(predicted_price=float(values.mean()), confidence=0.5)
