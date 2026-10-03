# ADR-002: Uso de pgvector para Almacenamiento e Indexación de Embeddings

- **Status**: Aceptado
- **Fecha**: 2026-08-20
- **Decisores**: Equipo de Arquitectura e Inteligencia Artificial

---

## Contexto
Para habilitar búsqueda semántica y recuperación aumentada (RAG) sobre licitaciones de ChileCompra, el sistema necesita almacenar representaciones vectoriales densas (embeddings) y realizar consultas de k-vecinos más cercanos (k-NN) por similitud de coseno.

## Decisión
Utilizar la extensión **`pgvector`** directamente sobre la base de datos PostgreSQL, implementando índices **HNSW** (`Hierarchical Navigable Small World`) con la métrica de distancia `vector_cosine_ops`.

## Alternativas Consideradas
1. **Bases de Datos Vectoriales Dedicadas (Pinecone / Qdrant / Weaviate / Milvus)**:
   - Excelente rendimiento especializado, pero introducen una segunda base de datos distribuida, aumentan la complejidad operacional, requieren sincronización dual y no permiten `JOINs` nativos con tablas relacionales de proveedores y adjudicaciones.
2. **Elasticsearch / OpenSearch (dense_vector)**:
   - Capacidad combinada de FTS y vector, pero consumo de memoria RAM elevado (JVM) y mayor overhead de mantenimiento.

## Consecuencias
- **Positivas**:
  - **Consultas Híbridas Nativas**: Permite ejecutar en una sola sentencia SQL filtros relacionales (`WHERE region_code = '13' AND fecha_cierre > now()`) junto con ordenamiento por similitud de coseno (`ORDER BY embedding <=> query_vector`).
  - **Cero Sincronización Dual**: Transaccionalidad ACID directa: si se inserta una licitación y falla el embedding, la transacción se revierte limpiamente.
  - **Baja Latencia**: Índices HNSW ofrecen respuestas sub-15ms sobre cientos de miles de vectores.
- **Negativas**:
  - Los índices HNSW consumen memoria RAM sustancial durante su construcción (`maintenance_work_mem`).
