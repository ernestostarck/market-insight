# Checklist y Puerta de Control de Release — Release Gate

Este documento define la **condición formal de salida a producción** (*Release Gate*) de **MercadoInsight**. Ningún despliegue a Staging o Producción puede autorizarse si no cumple de manera estricta y verificada con este checklist.

---

## 1. Categorías del Checklist de Release

### 1.1 Código (Code Quality & Tests)
- [x] **Lint**: `ruff check apps/backend` y `npm run lint` en frontend finalizan con cero errores.
- [x] **Typecheck**: `mypy apps/backend` y `npm run typecheck` en frontend pasan con cero violaciones de tipos.
- [x] **Unit Tests**: Pruebas unitarias de servicios, schemas y funciones con cobertura $\ge 80\%$.
- [x] **Integration Tests**: Pruebas de integración con base de datos PostgreSQL de test y endpoints FastAPI.
- [x] **E2E Tests**: Flujos críticos de navegación del dashboard y login verificados con Playwright.

### 1.2 Datos (Data & Migrations)
- [x] **Migrations**: Árbol de revisiones de Alembic con cabeza única (`single-head`), linealidad garantizada y migraciones reversibles (`downgrade()` probado).
- [x] **ETL Validation**: Pipeline de extracción y normalización validado contra muestras de ChileCompra con cero errores no controlados.
- [x] **Data Quality**: Comprobación de reglas de calidad (RUT válido, no nulos en PKs, frescura < 6h).

### 1.3 Inteligencia Artificial (AI & RAG)
- [x] **RAG Evaluation**: Respuestas evaluadas contra el Gold Dataset con $F_1$ Macro $\ge 90\%$ y exactitud de relevancia $\ge 95\%$.
- [x] **Prompt Tests**: Validación de prompts estructurados ante diversas intenciones de usuario.
- [x] **Grounding Tests**: Tasa de fidelidad (*grounding score*) $\ge 0.8$ en el 100% de las pruebas de regresión.
- [x] **Injection Tests**: Pruebas de inyección de prompt y consultas SQL destructivas bloqueadas por AST parser y rol `ai_analyst`.

### 1.4 Seguridad (Security Hardening)
- [x] **Dependency Scan**: `pip-audit` y `npm audit` sin vulnerabilidades críticas o altas (CVEs).
- [x] **Container Scan**: Escaneo de imágenes Docker con Trivy finalizado sin vulnerabilidades `CRITICAL`.
- [x] **Secret Scan**: Inspección de secretos en Git con `.gitignore` y `.dockerignore` validados.
- [x] **Auditoría Automatizada**: Ejecución exitosa de `python infrastructure/scripts/security-audit.py` (código de salida 0).

### 1.5 Infraestructura (Infrastructure & Observability)
- [x] **Docker Build**: Compilación limpia de imágenes multi-stage sin errores de caché ni capas de build residuales.
- [x] **Health Checks**: Endpoint `/health/ready` respondiendo `200 OK` con base de datos, Redis y MinIO listos.
- [x] **Backups**: Respaldo previo al release ejecutado con `backup.py` y verificación de integridad SHA-256 (`restore.py --verify-only`).
- [x] **Monitoring**: Exportadores Prometheus activos y tableros de Grafana recibiendo métricas.

### 1.6 Despliegue (Deployment & Promotion)
- [x] **Staging**: Despliegue preliminar ejecutado en el ambiente de staging bajo red aislada.
- [x] **Smoke Tests**: Pruebas de humo sobre `https://staging.mercadoinsight.cl` completadas exitosamente.
- [x] **Production**: Despliegue aprobado por el Tech Lead y ejecutado en ventana de bajo tráfico.
- [x] **Rollback Plan**: Plan de reversión probado y listo para activación inmediata en caso de contingencia.

---

## 2. Automatización del Release Gate (`release-check.py`)

Para automatizar la verificación en el pipeline de CI/CD:
```bash
python infrastructure/scripts/release-check.py
```
El script compila los resultados de cada sección y devuelve un código de salida `0` únicamente cuando todos los puntos mandatorios están aprobados.
