# Estrategia de Versionado — MercadoInsight

Este documento define las políticas de control de versiones, etiquetado en Git, sincronización con imágenes de contenedor y trazabilidad en producción para **MercadoInsight**, cumpliendo con la subfase **10.12 (Versionado)** de la Fase 10.

---

## 1. Adopción de Semantic Versioning (SemVer 2.0.0)

El proyecto adhiere estrictamente a la especificación [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html) utilizando el formato:

$$\text{MAJOR}.\text{MINOR}.\text{PATCH}$$

| Componente | Criterio de Incremento | Ejemplos en MercadoInsight |
| :--- | :--- | :--- |
| **`MAJOR`** | Cambios incompatibles con versiones previas (breaking changes). | Modificación o eliminación de rutas públicas `/api/v1`, reestructuración incompatible de tablas en `dw`, ruptura de contratos en schemas Pydantic. |
| **`MINOR`** | Nuevas funcionalidades que mantienen compatibilidad hacia atrás. | Nuevo endpoint REST analítico, nuevo algoritmo o modelo de embeddings NLP, nueva vista o dashboard en el frontend SPA. |
| **`PATCH`** | Corrección de errores (bug fixes) y parches de seguridad compatibles. | Corrección de cálculo en métricas de licitación, mitigación de vulnerabilidad en dependencia (CVE), ajuste en consultas SQL. |

---

## 2. Gestión del Changelog

Todos los cambios notables del proyecto se registran centralizadamente en [`CHANGELOG.md`](file:///c:/Users/artut/market-insight/CHANGELOG.md) siguiendo la especificación [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/):

1. **Sección `[Unreleased]`**: Acumula características y correcciones integradas a la rama `main` aún no empaquetadas en un release formal.
2. **Secciones de Release (`[X.Y.Z] - AAAA-MM-DD`)**: Congelan los cambios incluidos en cada tag de Git.
3. **Categorías estándar**: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.

---

## 3. Estrategia de Tags en Git

Las versiones se publican en el repositorio mediante tags Git anotados:

```bash
# Crear un tag anotado para release
git tag -a v1.0.0 -m "Release v1.0.0 — Producción MercadoInsight"

# Publicar el tag al repositorio remoto
git push origin v1.0.0
```

### Reglas de Etiquetado
* El prefijo obligatorio es `v` minúscula seguido de tres números (`v1.0.0`).
* Los tags son inmutables: nunca deben ser reasignados ni forzados (`--force`).
* Todo tag debe originarse desde un commit validado y testeado en la rama `main`.

---

## 4. Vinculación con Imágenes Docker (GHCR)

Cuando se genera un release o push a `main`, el pipeline de CI/CD genera los siguientes tags para las imágenes en **GitHub Container Registry (GHCR)**:

| Tag Docker | Propósito | Ejemplo |
| :--- | :--- | :--- |
| `latest` | Última compilación exitosa de la rama `main`. | `ghcr.io/ernestostarck/market-insight/backend:latest` |
| `short_sha` | Hash SHA inmutable para trazabilidad exacta y rollback determinista. | `ghcr.io/ernestostarck/market-insight/backend:a1b2c3d` |
| `vX.Y.Z` | Versión semántica formal asociada al tag de Git. | `ghcr.io/ernestostarck/market-insight/backend:v1.0.0` |
| `X.Y.Z` | Versión semántica sin prefijo para compatibilidad con orquestadores. | `ghcr.io/ernestostarck/market-insight/backend:1.0.0` |

---

## 5. Vinculación con Sentry y Observabilidad

El backend expone y reporta automáticamente la versión actual en la inicialización de **Sentry** y logs estructurados:

* **Sentry Release**: Configurado en [`setup_sentry()`](file:///c:/Users/artut/market-insight/apps/backend/app/core/sentry.py) como:
  ```python
  release = f"{current_settings.app_name}@{current_settings.app_version}"
  # Ejemplo: "MercadoInsight API@1.0.0"
  ```
* **Logs Estructurados**: Cada entrada de log emitida por el backend incluye el campo `"app_version": "1.0.0"` y `"environment"`.
* **OpenAPI / Swagger**: El esquema `/api/v1/openapi.json` refleja el campo `"version": "1.0.0"`.
* **Frontend SPA**: El pie de página y la consola de desarrollo exponen la versión compilada desde [`package.json`](file:///c:/Users/artut/market-insight/apps/frontend/package.json).

---

## 6. Sincronización en el Código Fuente

| Archivo | Parámetro | Valor Actual |
| :--- | :--- | :--- |
| [`apps/backend/pyproject.toml`](file:///c:/Users/artut/market-insight/apps/backend/pyproject.toml) | `project.version` | `"1.0.0"` |
| [`apps/frontend/package.json`](file:///c:/Users/artut/market-insight/apps/frontend/package.json) | `"version"` | `"1.0.0"` |
| [`apps/backend/app/core/settings.py`](file:///c:/Users/artut/market-insight/apps/backend/app/core/settings.py) | `app_version` (default) | `"1.0.0"` |
| [`CHANGELOG.md`](file:///c:/Users/artut/market-insight/CHANGELOG.md) | Release `[1.0.0]` | `2026-09-22` |
