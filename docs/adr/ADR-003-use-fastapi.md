# ADR-003: Uso de FastAPI para la Capa de API Backend

- **Status**: Aceptado
- **Fecha**: 2026-08-25
- **Decisores**: Equipo Backend

---

## Contexto
El backend requiere exponer endpoints REST de alta velocidad para consumo del dashboard React, endpoints de streaming para la IA conversacional (SSE) y compatibilidad directa con el ecosistema de Machine Learning / NLP de Python (scikit-learn, Sentence Transformers, Pydantic).

## Decisión
Adoptar **FastAPI** montado sobre el servidor ASGI **Uvicorn** como framework principal para la API REST de MercadoInsight.

## Alternativas Consideradas
1. **Django + Django REST Framework (DRF)**: Framework sumamente completo con ORM maduro, pero sobrecargado para una arquitectura orientada a servicios desacoplados y con menor rendimiento asíncrono nativo para streaming SSE.
2. **Flask**: Ligero y flexible, pero carece de validación canónica de tipos nativa (Pydantic), inyección de dependencias robusta y generación automática de OpenAPI 3.1.
3. **Node.js / Express / NestJS**: Gran rendimiento en I/O, pero genera una barrera lingüística al tener que desacoplar o comunicar vía RPC los modelos de NLP/AI construidos en Python.

## Consecuencias
- **Positivas**:
  - Documentación interactiva automática OpenAPI 3.1 (`/api/docs`, `/api/redoc`).
  - Validación tipada de peticiones y respuestas en tiempo de compilación/ejecución con Pydantic v2.
  - Soporte nativo para `async`/`await` y streaming Server-Sent Events (SSE) en respuestas de LLMs.
  - Sistema de inyección de dependencias (`Depends`) limpio para sesiones de SQLAlchemy y autenticación.
- **Negativas**:
  - Exige una disciplina estricta para no mezclar I/O síncrono bloqueante en funciones asíncronas (`async def`).
