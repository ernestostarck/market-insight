from dataclasses import dataclass

from app.core.settings import Settings, get_settings


@dataclass(slots=True)
class ChileCompraConfig:
    """Configuration for the internal ChileCompra SDK."""

    api_url: str
    api_ticket: str
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 0.5

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "ChileCompraConfig":
        active_settings = settings or get_settings()
        return cls(
            api_url=active_settings.chilecompra_api_url,
            api_ticket=active_settings.chilecompra_api_ticket,
            timeout=active_settings.chilecompra_timeout,
            max_retries=active_settings.chilecompra_max_retries,
            retry_delay=active_settings.chilecompra_retry_delay,
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_url and self.api_ticket)
