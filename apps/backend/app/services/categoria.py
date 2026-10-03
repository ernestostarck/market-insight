from app.repositories.categoria import CategoriaRepository
from app.schemas.categoria import CategoriaDetail


class CategoriaService:
    def __init__(self, repository: CategoriaRepository):
        self.repository = repository

    async def page(
        self,
        *,
        limit: int,
        anchor_id: int | None = None,
        direction: str = "next",
        q: str | None = None,
        monto_minimo: float | None = None,
    ):
        return await self.repository.get_page_filtered(
            limit=limit, anchor_id=anchor_id, direction=direction, q=q, monto_minimo=monto_minimo,
        )

    async def ranking(self, **kwargs):
        return await self.repository.get_ranking(**kwargs)

    async def get(self, categoria_id: int) -> CategoriaDetail | None:
        categoria = await self.repository.get_with_stats(categoria_id)
        if categoria is None:
            return None
        principales_proveedores = await self.repository.get_top_proveedores(categoria_id)
        principales_organismos = await self.repository.get_top_organismos(categoria_id)
        return CategoriaDetail(
            **categoria.model_dump(),
            principales_proveedores=principales_proveedores,
            principales_organismos=principales_organismos,
        )
