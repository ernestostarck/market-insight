"""Product extraction application service (Fase 6.18)."""

from __future__ import annotations

import uuid

from app.models.knowledge import Product
from app.nlp.dictionary import DomainDictionary, load_initial_dictionary
from app.nlp.product_attributes import ProductAttributes, extract_product_attributes
from app.nlp.product_concepts import ProductConceptMatch, match_product_concepts


class ProductExtractionService:
    def __init__(
        self,
        dictionary: DomainDictionary | None = None,
    ) -> None:
        self._dictionary = dictionary or load_initial_dictionary()

    def extract_product_concepts(self, text: str) -> tuple[ProductConceptMatch, ...]:
        return match_product_concepts(text, self._dictionary)

    def extract_product_attributes(self, text: str) -> ProductAttributes:
        return extract_product_attributes(text)

    def process_item(
        self,
        licitacion_id: int,
        licitacion_item_id: int,
        item_nombre: str,
        item_descripcion: str | None = None,
        cantidad: float | None = None,
        unidad: str | None = None,
        classification_id: uuid.UUID | None = None,
    ) -> list[Product]:
        combined_text = f"{item_nombre} {item_descripcion or ''}".strip()
        matched_concepts = self.extract_product_concepts(combined_text)
        attrs = self.extract_product_attributes(combined_text)

        products = []
        for concept in matched_concepts:
            p = Product(
                id=uuid.uuid4(),
                licitacion_id=licitacion_id,
                licitacion_item_id=licitacion_item_id,
                product_concept_id=0,  # mapped in DB or caller
                classification_id=classification_id,
                cantidad=cantidad,
                unidad=unidad,
                materiales=list(attrs.materiales) if attrs.materiales else None,
                dimensiones=attrs.dimensiones,
                capacidad=attrs.capacidad,
                caracteristicas_tecnicas=list(attrs.caracteristicas_tecnicas)
                if attrs.caracteristicas_tecnicas
                else None,
                confidence_score=1.0,
            )
            products.append(p)
        return products
