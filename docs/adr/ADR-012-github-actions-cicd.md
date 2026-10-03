# ADR-012: Adopción de GitHub Actions y GHCR para Pipelines de CI/CD

- **Status**: Aceptado
- **Fecha**: 2026-09-19
- **Decisores**: Equipo DevOps y Seguridad

---

## Contexto
El desarrollo colaborativo de MercadoInsight demanda validación continua de código (linting, formateo, pruebas unitarias y de integración), escaneos automáticos de seguridad (vulnerabilidades, dependencias y secretos) y despliegue automatizado hacia Staging y Producción.

## Decisión
Utilizar **GitHub Actions** como motor de integración y despliegue continuo (CI/CD), publicando los artefactos e imágenes de contenedores en **GitHub Container Registry (GHCR)** (`ghcr.io/ernestostarck/market-insight/*`).

## Alternativas Consideradas
1. **GitLab CI**: Excelente alternativa integrada, pero implicaría migrar el repositorio fuera de GitHub o mantener espejos sincronizados.
2. **Jenkins**: Servidor de CI/CD autoalojado flexible, pero genera una carga operacional permanente de parches de seguridad, plugins y administración de agentes runners.
3. **Docker Hub**: Registro estándar de imágenes, pero con cuotas de pull restrictivas en planes gratuitos en comparación con GHCR.

## Consecuencias
- **Positivas**:
  - Máxima integración con el repositorio de código, pull requests y control de acceso.
  - Workflows declarativos YAML modulares (`backend.yml`, `frontend.yml`, `security.yml`, `deploy.yml`).
  - Escaneos de seguridad automatizados con Trivy subiendo reportes en formato estándar SARIF a la pestaña de Security de GitHub.
- **Negativas**:
  - Dependencia de la disponibilidad y cuotas de minutos de runners de GitHub Actions.
