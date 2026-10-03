from collections.abc import Iterable
from typing import Generic, Protocol, TypeVar

T = TypeVar("T")
IdentifierT = TypeVar("IdentifierT")


class Repository(Protocol, Generic[T, IdentifierT]):
    """Generic repository contract."""

    def add(self, entity: T) -> T:
        """Persist a new entity."""

    def get(self, identifier: IdentifierT) -> T | None:
        """Load an entity by its identifier."""

    def list(self) -> Iterable[T]:
        """Return all entities."""

    def remove(self, identifier: IdentifierT) -> None:
        """Delete an entity by its identifier."""
