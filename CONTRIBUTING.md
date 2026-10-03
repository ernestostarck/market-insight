# Contributing

## Proposito

Este repositorio se desarrolla como una plataforma de inteligencia de mercado con enfoque profesional, modular y testeable.

## Reglas generales

- Mantener tipado completo con type hints.
- Documentar clases y funciones publicas con docstrings.
- Evitar duplicacion de logica.
- Preferir capas y contratos antes que implementaciones dispersas.
- Usar variables de entorno para toda configuracion sensible.
- No commitear secretos, tickets, API keys ni credenciales.

## Flujo de trabajo

1. Definir la fase y el alcance antes de tocar el codigo.
2. Implementar el modulo en la capa correcta.
3. Agregar pruebas para el comportamiento critico.
4. Validar con tests y chequeos de errores.
5. Actualizar documentacion si cambia el contrato.

## Estilo tecnico

- Backend en FastAPI con servicios, casos de uso, repositorios y adaptadores.
- Persistencia aislada en la capa de infraestructura.
- Integraciones externas encapsuladas en SDKs o clients.
- UI enfocada en analitica y decision support, no en CRUD basico.

## Proximos criterios de calidad

- Logging estructurado.
- Manejo robusto de errores.
- Integracion con CI/CD.
- Preparacion para Docker y despliegue en nube o VPS.
