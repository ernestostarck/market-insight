from dataclasses import dataclass


@dataclass(slots=True)
class SupplierScore:
    supplier_id: str
    score: float


class SupplierRanker:
    def rank(self, suppliers: list[SupplierScore]) -> list[SupplierScore]:
        return sorted(suppliers, key=lambda item: item.score, reverse=True)
