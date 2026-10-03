# Arquitectura RAG e Inteligencia Conversacional — MercadoInsight AI

Este documento describe la arquitectura técnica, los contratos y los componentes del subsistema **MercadoInsight AI (Fase 9)**.

---

## 1. Visión y Principio Fundamental

> **MercadoInsight no es "un ChatGPT conectado a PostgreSQL", sino un motor de inteligencia de compras públicas con una interfaz conversacional.**

La IA debe responder exclusivamente a partir de **evidencia recuperable y verificable**, eliminando las alucinaciones y garantizando trazabilidad total mediante citas directas (*Sources*).

```text
React Chat
    ↓
FastAPI (/api/v1/ai/conversations)
    ↓
Conversation & Session Engine (PostgreSQL + Redis)
    ↓
Intent Detection (Clasificación de Intención)
    ↓
Query Planner (Planificador Determinístico)
    ↓
┌───────────────────────┬────────────────────────┐
│                       │                        │
▼                       ▼                        ▼
SQL Engine          pgvector RAG             Hybrid Search
(Cuantitativo)       (Semántico)           (Filtros + Vector)
│                       │                        │
└───────────────────────┼────────────────────────┘
                        ↓
                 Context Builder
                        ↓
              LLM Gateway (Agnóstico)
                        ↓
             Grounding & Source Citations
                        ↓
              Respuesta + Fuentes
```

---

## 2. Separación de Estrategias: SQL vs. Semántico vs. Híbrido

Uno de los errores más comunes en arquitecturas RAG es pretender que el LLM realice cálculos matemáticos o agregaciones cuantitativas sobre documentos fragmentados. En MercadoInsight, la distinción es taxativa:

| Tipo de Pregunta | Ejemplo | Estrategia Elegida | Motor Ejecutor |
| :--- | :--- | :--- | :--- |
| **Cuantitativa / Gasto** | "¿Cuánto gastó la Municipalidad de Santiago en 2025 en insumos médicos?" | `SQL` | Data Warehouse (`dw.fact_*`, `marts.*`) |
| **Comparativa** | "Compara los 3 principales proveedores de sillas de ruedas por monto adjudicado." | `SQL` | Consultas analíticas SQL con ordenamiento y límites |
| **Semántica / Requisitos** | "Busca licitaciones orientadas a inclusión laboral o apoyo a personas en situación de discapacidad." | `SEMANTIC` | Búsqueda por similitud vectorial con `pgvector` en `knowledge.embeddings` |
| **Híbrida** | "Encuentra licitaciones de tecnología asistiva de municipios de la Región Metropolitana durante 2024." | `HYBRID` | Filtros relacionales (`region_code = '13'`, `year = 2024`) combinados con cosine distance en embeddings |
| **Directa / Ficha** | "¿Cuál es el estado de la licitación `1000-01-LR26`?" | `DIRECT` / `SQL` | Búsqueda por clave primaria o índice único en `core.licitaciones` |

---

## 3. Contratos de Datos y Flujo de Componentes

### 3.1 `QueryPlan`
Estructura formulada por el planificador determinístico:
- `intent`: Intención clasificada (`search`, `spending_analysis`, `semantic_search`, etc.).
- `retrieval_strategy`: Estrategia (`sql`, `semantic`, `hybrid`, `direct`).
- `sql_query` / `parameters`: Consulta parametrizada segura en caso de consultas estructuradas.
- `semantic_query` / `filters`: Consulta textual para embedding y filtros de metadata.

### 3.2 `Source` y `RetrievalResult`
Todo dato recuperado se normaliza en objetos `Source`:
- `id`: Identificador único (código de licitación, RUT, ID de orden de compra o fragmento de documento).
- `source_type`: Tipo de entidad (`tender`, `purchase_order`, `buyer`, `supplier`, `mart`, `chunk`).
- `title` y `snippet`: Extracto textual legible y verificable por el usuario.
- `url`: Enlace directo o deep-link en MercadoInsight.
- `score`: Similitud de coseno o relevancia del resultado.

### 3.3 `Context` y `GroundingResult`
El `ContextBuilder` ensambla las fuentes en un formato de prompt estructurado:
- El LLM genera la respuesta citando las fuentes disponibles.
- El `GroundingValidator` analiza que cada afirmación numérica y factual provenga del contexto provisto, calculando un `grounding_score` entre `0.0` y `1.0`.

---

## 4. Desacoplamiento de Proveedores LLM

Los contratos definidos en `app.ai.interfaces.LLMGateway` permiten utilizar cualquier backend sin alterar el código de la aplicación:
- Adaptadores para OpenAI, Anthropic Claude, Google Gemini o modelos locales (Ollama/vLLM).
- Mocks determinísticos para entornos de CI/CD y pruebas unitarias rápidas sin llamadas de red externas.
