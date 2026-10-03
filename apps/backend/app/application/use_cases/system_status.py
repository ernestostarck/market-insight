from dataclasses import dataclass

from app.core.settings import Settings


@dataclass(slots=True)
class SystemStatus:
    """Application-level status payload."""

    status: str
    service: str
    version: str
    environment: str


class SystemStatusUseCase:
    """Return the current API status metadata."""

    def execute(self, settings: Settings) -> SystemStatus:
        return SystemStatus(
            status="ok",
            service=settings.app_name,
            version=settings.app_version,
            environment=settings.environment,
        )
