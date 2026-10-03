# Pipeline Conversacional RAG & Text-to-SQL

Este documento detalla la arquitectura, el diseño de componentes y el flujo de ejecución del subsistema de **Retrieval-Augmented Generation (RAG)** e Inteligencia Conversacional de **MercadoInsight**.

---

## 1. Estrategia Dual de Recuperación

MercadoInsight resuelve uno de los problemas fundamentales de los asistentes con LLMs: **la incapacidad de calcular matemáticas o agregaciones sobre texto no estructurado**. Para ello, clasifica de forma determinística la intención de la consulta:

```text
                               Consulta del Usuario
                                         │
                                         ▼
                            Clasificador de Intención
                                         │
            ┌────────────────────────────┼────────────────────────────┐
            ▼                            ▼                            ▼
   Consultas Cuantitativas      Consultas Semánticas          Consultas Híbridas
  ("¿Cuánto gastó X en 2024?")  ("Licitaciones de inclusión") ("Insumos en Biobío 2025")
            │                            │                            │
            ▼                            ▼                            ▼
   Generador Text-to-SQL         Búsqueda pgvector           Filtros SQL + pgvector
   (Data Warehouse / Marts)     (Distancia Coseno HNSW)         (Ponderación RRF)
            │                            │                            │
            └────────────────────────────┼────────────────────────────┘
                                         ▼
                             Normalización de Fuentes
                                (Objeto `Source`)
                                         ▼
                             Constructor de Contexto
                                         ▼
                            LLM Gateway (Prompt Seguro)
                                         ▼
                            Validador de Grounding
                                         ▼
                            Respuesta Final + Citas
```

---

## 2. Contratos de Datos Centrales

### 2.1 `QueryPlan`
Objeto generado por el planificador determinístico:
```python
class QueryPlan(BaseModel):
    intent: IntentType  # quantitative, semantic, hybrid, direct_lookup
    strategy: RetrievalStrategy  # sql, vector, hybrid
    sql_query: Optional[str] = None
    sql_parameters: Dict[str, Any] = Field(default_factory=dict)
    semantic_query: Optional[str] = None
    filters: Dict[str, Any] = Field(default_factory=dict)
```

### 2.2 `Source`
Todo fragmento o dato numérico provisto al modelo se formatea en un objeto `Source`:
- `id`: Código de licitación, RUT o ID de hecho analítico.
- `title`: Título legible de la fuente.
- `snippet`: Texto o resumen cuantitativo factual.
- `score`: Nivel de relevancia o similitud coseno.
- `url`: Enlace directo a la ficha dentro de MercadoInsight.

---

## 3. Streaming de Respuestas (SSE)

Las respuestas hacia el cliente React se transmiten en tiempo real mediante **Server-Sent Events** en `/api/v1/chat/conversations/{id}/messages/stream`:
1. Evento `sources`: Envío preliminar de las fuentes identificadas para renderizado inmediato de tarjetas de evidencia.
2. Eventos `token`: Flujo continuo de fragmentos de texto generados por el LLM.
3. Evento `done`: Metadatos de cierre, tokens consumidos, costo calculado en USD y `grounding_score`.
