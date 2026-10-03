# Evaluación y Validación de Modelos de IA

Este documento describe el marco de evaluación continua, benchmarking con dataset Gold y métricas de desempeño de la inteligencia artificial de **MercadoInsight**.

---

## 1. Métricas de Desempeño NLP (Fase 7)

Evaluadas sobre el **Gold Dataset** de 20 licitaciones representativas de Mercado Público (ChileCompra), especializadas en geriatría, ayudas técnicas y discapacidad:

| Métrica | Definición | Resultado Alcanzado | Umbral Mínimo Requerido |
| :--- | :--- | :--- | :--- |
| **$F_1$ Macro** | Media armónica entre precisión y recall en categorías | **90.5%** | $\ge 85.0\%$ |
| **Exactitud Categórica** | Acierto en asignación de rama taxonómica | **90.0%** | $\ge 85.0\%$ |
| **Exactitud de Relevancia** | Determinación de pertinencia al nicho geriátrico | **95.0%** | $\ge 90.0\%$ |
| **Latencia Media** | Tiempo de procesamiento por documento en CPU | **1.6 ms** | $\le 50.0\text{ ms}$ |

---

## 2. Métricas de Evaluación RAG (Fase 9)

El subsistema conversacional es auditado bajo el estándar de evaluación de fidelidad y relevancia:

1. **Puntuación de Grounding (*Faithfulness Score*)**:
   - Mide qué proporción de las afirmaciones factuales y numéricas en la respuesta están explícitamente contenidas en las fuentes provistas.
   - Umbral de alerta en Prometheus: Si la tasa de respuestas con `grounding_score < 0.8` excede el 10% en 15 minutos, se dispara `AIGroundingFailureRateHigh`.
2. **Relevancia de la Respuesta (*Answer Relevance*)**:
   - Coincidencia semántica entre la pregunta del usuario y la respuesta sintetizada.
3. **Calidad de Recuperación (*Retrieval Recall & MRR*)**:
   - Proporción de documentos relevantes recuperados en el Top-5 mediante búsqueda híbrida.

---

## 3. Circuito de Retroalimentación Humana (Human-in-the-Loop)

- **Calificación en la UI**: El usuario puede marcar con pulgar arriba / pulgar abajo cada respuesta del asistente en React.
- **Reporte de Alucinación o Error Factual**: Un analista puede corregir el dato factual directo en el modal de feedback.
- **Incorporación al Gold Dataset**: Las correcciones validadas por analistas sénior son integradas periódicamente a la suite de regresión automatizada (`pytest apps/backend/tests/ai/`).
