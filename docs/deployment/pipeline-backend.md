# Pipeline de Backend — MercadoInsight

Este documento detalla los controles de calidad, pruebas automatizadas, análisis estático de seguridad y empaquetado ejecutados por el workflow [`backend.yml`](file:///c:/Users/artut/market-insight/.github/workflows/backend.yml).

---

## 1. Etapas del Pipeline

```text
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  1. Linter   │ ──> │ 2. Typecheck │ ──> │   3. Tests   │ ──> │ 4. Seguridad │
│ (Ruff Check) │     │    (Mypy)    │     │(Pytest + Cov)│     │(Bandit/Audit)│
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                       │
                                                                       ▼
                                                               ┌──────────────┐
                                                               │5. Build Docker│
                                                               │ (API + Worker)│
                                                               └──────────────┘
```

---

## 2. Descripción Detallada de Controles

### 2.1 Linter y Formato (`ruff`)
* **Herramienta**: Ruff (analizador y formateador ultrarrápido en Rust).
* **Comandos**:
  ```bash
  ruff check app tests
  ruff format --check app tests
  ```
* **Políticas**: Detección de imports no utilizados, errores de sintaxis, variables sin usar y estandarización PEP 8.

### 2.2 Verificación de Tipos Estáticos (`mypy`)
* **Herramienta**: Mypy con anotaciones de tipo Python 3.13+.
* **Comando**:
  ```bash
  mypy app --ignore-missing-imports
  ```
* **Objetivo**: Prevenir errores de `NoneType`, desajustes en esquemas Pydantic y firmas de funciones incompatibles antes de la ejecución.

### 2.3 Suite de Pruebas y Cobertura (`pytest`)
* **Herramienta**: Pytest con `pytest-asyncio` y `pytest-cov`.
* **Comando**:
  ```bash
  pytest tests -q --cov=app --cov-report=xml:test-results/coverage.xml --junitxml=test-results/junit.xml
  ```
* **Filtros**: Exclusión de pruebas lentas o que requieren dependencias de hardware externas en PRs rápidos (`-m 'not slow and not integration'`).
* **Artefactos**: El reporte de ejecución `junit.xml` y la cobertura `coverage.xml` se publican como artefactos del build para inspección.

### 2.4 Análisis de Seguridad Estático (SAST con `bandit`)
* **Herramienta**: Bandit (analizador de vulnerabilidades comunes de seguridad en código Python).
* **Comando**:
  ```bash
  bandit -r app -ll -ii
  ```
* **Filtros**: Notifica y bloquea ante issues de severidad media y alta (`-ll`) y confianza media y alta (`-ii`), como inyecciones SQL en raw queries, uso de generadores pseudoaleatorios inseguros para tokens o deserialización insegura.

### 2.5 Auditoría de Dependencias Vulnerables (`pip-audit`)
* **Herramienta**: `pip-audit` conectado a la base de datos de PyPI / Open Source Vulnerabilities (OSV).
* **Comando**:
  ```bash
  pip-audit
  ```
* **Objetivo**: Asegurar que ninguna biblioteca instalada en producción contenga vulnerabilidades conocidas (CVEs reportadas).

### 2.6 Validación de Migraciones de Base de Datos
* Verificación de consistencia del árbol de migraciones Alembic en `apps/backend/alembic/versions/` para evitar branches divergentes o números de revisión duplicados.

### 2.7 Compilación de Contenedores y Publicación
* Construcción con Docker Buildx multi-stage:
  - Imagen API: [`Dockerfile.prod`](file:///c:/Users/artut/market-insight/apps/backend/Dockerfile.prod) -> `ghcr.io/ernestostarck/market-insight/backend`
  - Imagen Worker: [`Dockerfile.worker.prod`](file:///c:/Users/artut/market-insight/apps/backend/Dockerfile.worker.prod) -> `ghcr.io/ernestostarck/market-insight/worker`
* Se utiliza GitHub Actions Cache (`cache-to: type=gha`) para reutilizar capas intermedias y acelerar los builds subsiguientes a menos de 2 minutos.
* Publicación automática en el registro inmutable GHCR ante cada push a la rama `main`.

