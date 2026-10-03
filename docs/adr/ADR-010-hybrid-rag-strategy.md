# ADR-010: Estrategia de RAG Híbrido con Clasificación Determinística de Intención

- **Status**: Aceptado
- **Fecha**: 2026-09-16
- **Decisores**: Equipo de Inteligencia Artificial y Datos

---

## Contexto
Los usuarios analistas formulan preguntas analíticas muy dispares al Asistente Conversacional: algunas requieren sumas cuantitativas complejas (ej. *"¿Cuánto gastó el Hospital Regional en 2024?"*) mientras que otras son conceptuales o de síntesis (ej. *"¿Qué requisitos de solvencia piden para postular?"*). Alimentar fragmentos de texto no estructurados a un LLM para que calcule sumas matemáticas genera alucinaciones severas.

## Decisión
Implementar un planificador determinístico de consultas (`QueryPlanner`) que clasifica la intención antes de recuperar datos:
- Si la intención es **cuantitativa / agregada**: Se genera y ejecuta una consulta SQL de solo lectura sobre el Data Warehouse (`dw`/`marts`).
- Si la intención es **semántica / requisitos**: Se recuperan fragmentos relevantes mediante `pgvector` sobre `knowledge.embeddings`.
- Si la intención es **híbrida**: Se combinan filtros relacionales SQL con búsqueda vectorial (RRF).

## Alternativas Consideradas
1. **RAG Naive Clásico (Solo Búsqueda Vectorial)**: Fragmentar bases en chunks de 500 tokens y enviar los chunks más similares al LLM. Falla estrepitosamente en preguntas cuantitativas de totales de gasto y comparativas.
2. **Text-to-SQL Puro para Todas las Preguntas**: Excelente para datos tabulares, pero incapaz de responder preguntas semánticas sobre descripciones cualitativas de bases técnicas.

## Consecuencias
- **Positivas**:
  - Eliminación total de alucinaciones matemáticas en cifras de gasto y adjudicaciones.
  - Trazabilidad y explicabilidad: Cada respuesta incluye la consulta SQL ejecutada o las fuentes vectoriales citadas.
- **Negativas**:
  - Mayor complejidad en la capa intermedia de orquestación y necesidad de mantener un esquema relacional dimensional optimizado.
