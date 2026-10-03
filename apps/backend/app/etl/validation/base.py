from typing import Protocol

from app.etl.models import StoredRawRecord, ValidationResult


class RecordValidator(Protocol):
    def validate(self, record: StoredRawRecord) -> ValidationResult: ...
