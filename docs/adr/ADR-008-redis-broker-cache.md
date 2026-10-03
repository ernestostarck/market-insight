# ADR-008: Uso de Redis como Broker de Celery y Capa de Caché

- **Status**: Aceptado
- **Fecha**: 2026-09-12
- **Decisores**: Equipo Backend y Arquitectura

---

## Contexto
El sistema ejecuta tareas asíncronas pesadas (ingesta ETL y cálculo de embeddings NLP) y consultas analíticas repetitivas sobre licitaciones activas. Se requería una solución rápida y probada para la gestión de colas de mensajes y caché en memoria.

## Decisión
Implementar **Redis 7 Alpine** como broker de colas para **Celery** y como almacenamiento en memoria para caché de sesiones y respuestas de alta frecuencia.

## Alternativas Consideradas
1. **RabbitMQ**: Broker de mensajería AMQP altamente especializado y robusto para colas complejas, pero mayor consumo de memoria (Erlang) y no provee capacidades de caché clave-valor para respuestas HTTP.
2. **PostgreSQL como Broker (con Celery / Arq)**: Evita un servicio adicional, pero genera contención de bloqueos e I/O innecesario en la base de datos relacional principal.

## Consecuencias
- **Positivas**:
  - Un único servicio resuelve tanto el encolamiento de Celery como la caché rápida de la API.
  - Latencias de lectura/escritura sub-milisegundo en memoria RAM.
  - Soporte de políticas automáticas de desalojo (`volatile-lru`).
- **Negativas**:
  - Toda la información en caché es volátil si no se configura persistencia RDB/AOF (adecuado para nuestro caso, ya que el estado maestro reside en PostgreSQL).
