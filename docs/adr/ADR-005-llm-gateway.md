# ADR-005: Desacoplamiento de Proveedores LLM mediante Interfaz LLMGateway

- **Status**: Aceptado
- **Fecha**: 2026-09-02
- **Decisores**: Equipo de Inteligencia Artificial y Arquitectura

---

## Contexto
El subsistema conversacional RAG interactúa con modelos de lenguaje masivos para la síntesis de respuestas y generación de SQL. Acoplar la aplicación directamente a la librería SDK de un único proveedor (como OpenAI) genera dependencia técnica (*vendor lock-in*), dificulta la ejecución de pruebas unitarias en CI/CD sin consumo de créditos y bloquea el uso de modelos locales (Ollama/vLLM) en el futuro.

## Decisión
Diseñar e implementar el contrato abstracto `LLMGateway` (`app.ai.interfaces.LLMGateway`), abstrayendo métodos como `generate_chat_completion()` y `stream_chat_completion()`. La aplicación interactúa exclusivamente contra esta interfaz mediante Inyección de Dependencias.

## Alternativas Consideradas
1. **Acoplamiento Directo con `openai-python`**: Implementación rápida inicial, pero imposibilita cambiar de proveedor o correr tests unitarios offline sin conexiones de red externas.
2. **Frameworks Pesados (LangChain / LlamaIndex)**: Proveen abstracciones de múltiples proveedores, pero introducen dependencias sobredimensionadas, breaking changes frecuentes entre versiones menores y opacidad en el manejo de prompts y streaming SSE.

## Consecuencias
- **Positivas**:
  - Posibilidad de alternar entre OpenAI (gpt-4o, gpt-4o-mini), Anthropic Claude, Google Gemini o modelos locales sin modificar los enrutadores ni servicios.
  - Implementación de `MockLLMGateway` determinístico para suites de CI/CD, permitiendo pruebas automáticas en verde sin gastar tokens ni depender de APIs externas.
  - Trazabilidad y gobernanza de costos centralizada en el interceptor del gateway (`CostTracker`).
- **Negativas**:
  - Requiere mantener adaptadores específicos por cada proveedor que se desee soportar formalmente.
