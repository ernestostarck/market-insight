from pydantic import BaseModel, ConfigDict, Field


class CategoriaProveedorItem(BaseModel):
    """One of a categoria's top suppliers by amount awarded."""

    proveedor_id: int
    proveedor_nombre: str | None
    proveedor_rut: str | None
    monto_adjudicado: float
    cuota: float = Field(..., description="Share of the categoria's total awarded amount, in percent.")


class CategoriaOrganismoItem(BaseModel):
    """One of a categoria's top buyers by amount purchased."""

    organismo_id: int
    organismo_nombre: str | None
    monto_comprado: float
    total_licitaciones: int


def split_rubro_breadcrumb(nombre: str | None) -> tuple[str | None, str | None, str | None]:
    """Split ChileCompra's own `Categoria` field into its real segmento/familia/clase
    parts. Each tender item's `Categoria` is itself a "Segmento / Familia / Clase"
    breadcrumb string (e.g. "Ropa, maletas y productos de aseo personal / Ropa /
    Uniformes") — this only parses that real value, it does not synthesize one."""
    if not nombre:
        return None, None, None
    parts = [part.strip() or None for part in nombre.split(" / ")]
    parts += [None] * (3 - len(parts))
    return parts[0], parts[1], parts[2]


class Categoria(BaseModel):
    """A ChileCompra rubro (`core.categoria`), with real award stats.

    Sourced from each tender's own `CodigoCategoria`/`Categoria` (its item-level
    rubro classification). `Categoria` is a "Segmento / Familia / Clase" breadcrumb
    string; `segmento`/`familia`/`clase` below are that same string split into its
    real parts (see `split_rubro_breadcrumb`), not a derived/simulated hierarchy.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Internal numeric identifier.")
    codigo: str | None = Field(None, description="ChileCompra's own rubro code.")
    nombre: str | None = Field(None, description="Rubro name, as ChileCompra reports it.")
    segmento: str | None = Field(None, description="UNSPSC segmento — first part of ChileCompra's breadcrumb.")
    familia: str | None = Field(None, description="UNSPSC familia — second part of ChileCompra's breadcrumb.")
    clase: str | None = Field(None, description="UNSPSC clase — third/leaf part of ChileCompra's breadcrumb.")
    total_licitaciones: int = Field(0, description="Tenders whose dominant rubro is this categoria.")
    monto_total: float = Field(0, description="Sum of monto_adjudicado across those tenders' awards.")
    total_proveedores: int = Field(0, description="Distinct suppliers awarded in this categoria.")
    total_organismos: int = Field(0, description="Distinct buyers that published tenders in this categoria.")


class CategoriaDetail(Categoria):
    principales_proveedores: list[CategoriaProveedorItem] = Field(default_factory=list)
    principales_organismos: list[CategoriaOrganismoItem] = Field(default_factory=list)
