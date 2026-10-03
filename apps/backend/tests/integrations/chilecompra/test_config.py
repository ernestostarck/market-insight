from app.core.settings import Settings
from app.integrations.chilecompra.config import ChileCompraConfig


def test_chilecompra_config_reads_sdk_settings() -> None:
    settings = Settings(
        CHILECOMPRA_API_URL="https://api.mercadopublico.cl/servicios/v1/publico",
        CHILECOMPRA_API_TICKET="ticket-123",
        CHILECOMPRA_TIMEOUT="45",
        CHILECOMPRA_MAX_RETRIES="5",
        CHILECOMPRA_RETRY_DELAY="1.25",
    )

    config = ChileCompraConfig.from_settings(settings)

    assert config.api_url == "https://api.mercadopublico.cl/servicios/v1/publico"
    assert config.api_ticket == "ticket-123"
    assert config.timeout == 45.0
    assert config.max_retries == 5
    assert config.retry_delay == 1.25
    assert config.is_configured is True
