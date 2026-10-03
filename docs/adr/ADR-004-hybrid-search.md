# ADR-004: Adopción de Búsqueda Híbrida con Reciprocal Rank Fusion (RRF)

- **Status**: Aceptado
- **Fecha**: 2026-08-28
- **Decisores**: Equipo de Búsqueda y Procesamiento de Lenguaje Natural

---

## Contexto
En compras públicas coexisten dos realidades de búsqueda:
1. **Búsqueda léxica de precisión**: Códigos de licitación exactos, marcas de fármacos, números de serie y modelos (donde los embeddings vectoriales suelen fallar o diluir la relevancia).
2. **Búsqueda semántica conceptual**: Intenciones amplias (ej. *"ayudas técnicas para adultos mayores"* donde los términos exactos no aparecen en el título).

## Decisión
Implementar un motor de **Búsqueda Híbrida** que fusiona los resultados de **PostgreSQL Full-Text Search (FTS)** en español (`tsvector` + `ts_rank_cd`) y **Similitud Coseno Vectorial (`pgvector`)**, unificando sus ordenamientos mediante el algoritmo **Reciprocal Rank Fusion (RRF)**:
$$\text{Score}(d) = \sum_{m \in \{\text{FTS}, \text{Vector}\}} \frac{1}{k + \text{rank}_m(d)} \quad (k=60)$$

## Alternativas Consideradas
1. **Solo Búsqueda Léxica (BM25 / FTS)**: Incapaz de encontrar licitaciones relevantes que empleen sinónimos técnicos o términos coloquiales.
2. **Solo Búsqueda Vectorial (Embeddings)**: Frecuentes falsos positivos en números de modelo exactos (ej. confunde `Cama-2024` con `Cama-2026`).
3. **Ponderación Lineal Directa de Scores**: Normalizar y sumar $\alpha \cdot \text{Score}_{\text{FTS}} + (1-\alpha) \cdot \text{Score}_{\text{Vector}}$ resulta inestable debido a que las escalas de similitud de coseno y BM25 no son comparables directamente.

## Consecuencias
- **Positivas**:
  - Máxima recall y precisión tanto para consultas técnicas como para términos comerciales abiertos.
  - Robustez algorítmica: RRF es invariante a las escalas internas de los motores al trabajar con posiciones relativas de ranking.
- **Negativas**:
  - Requiere ejecutar dos consultas paralelas o subconsultas en PostgreSQL antes de combinar la lista final en memoria/SQL.
