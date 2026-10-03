from dataclasses import dataclass

import httpx

from app.core.config import get_settings


@dataclass(slots=True)
class ChileCompraClient:
    base_url: str
    api_key: str

    @classmethod
    def from_settings(cls) -> "ChileCompraClient":
        settings = get_settings()
        return cls(base_url=settings.chilecompra_base_url, api_key=settings.chilecompra_api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
        }

    def _params(self, **kwargs: str) -> dict[str, str]:
        params = {"ticket": self.api_key}
        params.update({key: value for key, value in kwargs.items() if value})
        return params

    async def list_licitaciones(
        self,
        estado: str | None = None,
        codigo: str | None = None,
    ) -> dict[str, object]:
        params = self._params(estado=estado or "", codigo=codigo or "")

        async with httpx.AsyncClient(base_url=self.base_url, headers=self._headers(), timeout=30.0) as client:
            response = await client.get("/licitaciones.json", params=params)
            response.raise_for_status()
            return response.json()

    async def list_tenders(self, estado: str | None = None) -> list[dict[str, object]]:
        payload = await self.list_licitaciones(estado=estado)
        listado = payload.get("Listado", []) if isinstance(payload, dict) else []
        return listado if isinstance(listado, list) else []

    async def get_licitacion(self, codigo: str) -> dict[str, object]:
        params = self._params(codigo=codigo)

        async with httpx.AsyncClient(base_url=self.base_url, headers=self._headers(), timeout=30.0) as client:
            response = await client.get("/licitaciones.json", params=params)
            response.raise_for_status()
            payload = response.json()
            return payload if isinstance(payload, dict) else {"Listado": payload}
