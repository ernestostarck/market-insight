# MercadoInsight

> **MercadoInsight** es una plataforma de inteligencia de mercado basada en datos de contratación pública de ChileCompra / Mercado Público, orientada al análisis de oportunidades, proveedores, organismos, categorías, precios y tendencias, incorporando búsqueda semántica e IA conversacional.

[![CI Backend](https://github.com/ernestostarck/market-insight/actions/workflows/backend.yml/badge.svg)](https://github.com/ernestostarck/market-insight/actions/workflows/backend.yml)
[![CI Frontend](https://github.com/ernestostarck/market-insight/actions/workflows/frontend.yml/badge.svg)](https://github.com/ernestostarck/market-insight/actions/workflows/frontend.yml)
[![Security Scan](https://github.com/ernestostarck/market-insight/actions/workflows/security.yml/badge.svg)](https://github.com/ernestostarck/market-insight/actions/workflows/security.yml)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## Tabla de Contenidos

1. [Overview](#1-overview)
2. [Features](#2-features)
3. [Architecture](#3-architecture)
4. [Tech Stack](#4-tech-stack)
5. [Screenshots / UI Walkthrough](#5-screenshots--ui-walkthrough)
6. [Installation](#6-installation)
7. [Development](#7-development)
8. [Testing](#8-testing)
9. [Deployment](#9-deployment)
10. [API](#10-api)
11. [AI / RAG](#11-ai--rag)
12. [Data](#12-data)
13. [Monitoring](#13-monitoring)
14. [Security](#14-security)
15. [Roadmap](#15-roadmap)
16. [License](#16-license)

---

## 1. Overview

MercadoInsight transforma los datos abiertos y la API de compras públicas de Chile (ChileCompra / Mercado Público) en **inteligencia de mercado accionable**, con un foco estratégico en accesibilidad, seguridad geriátrica y personas en situación de discapacidad.

### Problema que Resuelve
- **Asimetría de Información**: Millones de registros de licitaciones públicas dispersos y heterogéneos dificultan identificar oportunidades comerciales a tiempo.
- **Opacidad de Precios y Concentración**: Complejidad para calcular precios de referencia reales por ítem e identificar proveedores dominantes por rubro y organismo.
- **Inexistencia de Búsqueda Semántica Especializada**: La búsqueda oficial por palabras clave omite licitaciones que usan sinónimos técnicos (ej. *ortesis, bipedestador, ayudas técnicas, movilidad reducida*).
- **Incapacidad Analítica de LLMs Tradicionales**: Los chatbots genéricos sufren alucinaciones numéricas al calcular gasto público. MercadoInsight soluciona esto combinando Text-to-SQL determinístico con RAG de fuentes citadas.

---

## 2. Features

- 🔍 **Búsqueda Híbrida Inteligente**: Fusión RRF entre Full-Text Search en español y búsqueda vectorial semántica con `pgvector` e índices HNSW.
- 🏢 **Perfiles 360° de Proveedores y Organismos**: Métricas de participación, tasa de adjudicación, montos acumulados y concentración de mercado.
- 🎯 **Scoring de Oportunidad y Riesgo**: Algoritmos de scoring multidimensional para priorizar licitaciones según pertinencia y ventana comercial.
- 💬 **Asistente Conversacional RAG**: Chatbot especializado en compras públicas con respuestas basadas exclusivamente en fuentes citadas y streaming en tiempo real (SSE).
- ⚙️ **Pipeline ETL con Cuarentena**: Ingesta automática (API y Bulk), deduplicación por hash SHA-256 y aislamiento de datos defectuosos sin detener el flujo.
- 📊 **Dashboards Ejecutivos**: Visualizaciones de series temporales de gasto público con Apache ECharts y mapas territoriales con Leaflet.
- 🛡️ **Endurecimiento y Gobernanza**: Monitoreo de costos de IA por token, guardrails SQL de solo lectura y aislamiento de red en dos niveles (`public-net` y `private-net`).

---

## 3. Architecture

El sistema adopta **Clean Architecture**, **SOLID**, **Domain-Driven Design (DDD) ligero** y el **Modelo C4**:

```text
                             INTERNET
                                │
                        [ Puertos 80/443 ]
                                ▼
                       ┌─────────────────┐
                       │  NGINX Ingress  │ (SSL Termination, Rate Limit, WAF)
                       └────────┬────────┘
                                │
                        RED PÚBLICA (public-net)
                                │
                 ┌──────────────┴──────────────┐
                 ▼                             ▼
        ┌─────────────────┐           ┌─────────────────┐
        │  Frontend SPA   │           │ FastAPI Backend │
        │   (React 18)    │           │   (Uvicorn)     │
        └─────────────────┘           └────────┬────────┘
                                               │
                                       RED PRIVADA (private-net)
                                               │
        ┌──────────────┬──────────────┬────────┴─────┬──────────────┬──────────────┐
        ▼              ▼              ▼              ▼              ▼              ▼
 ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
 │ PostgreSQL │ │   Redis    │ │   MinIO    │ │   Celery   │ │ Prometheus │ │    Loki    │
 │ (pgvector) │ │  (Cache)   │ │  (Storage) │ │  Workers   │ │ (Métricas) │ │   (Logs)   │
 └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘
```

Diagramas formales C4 (Contexto, Contenedores, Componentes) disponibles en [ARCHITECTURE.md](ARCHITECTURE.md) y [docs/architecture/overview.md](docs/architecture/overview.md).

---

## 4. Tech Stack

| Capa | Tecnologías Principales |
| :--- | :--- |
| **Backend** | Python 3.14, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, Celery |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, Zustand, ECharts, Leaflet |
| **Base de Datos** | PostgreSQL 17, `pgvector` (HNSW), `pg_trgm`, `unaccent`, PostGIS |
| **Almacenamiento y Caché** | Redis 7 (broker y caché), MinIO (object storage S3 compatible) |
| **IA & NLP** | Sentence Transformers (`all-MiniLM-L6-v2`), scikit-learn, OpenAI API Gateway, Text-to-SQL |
| **Observabilidad** | Prometheus, Grafana (8 dashboards), Loki, Promtail, Alertmanager, Sentry, OpenTelemetry |
| **Infraestructura & CI/CD** | Docker multi-stage, Docker Compose v2, NGINX, GitHub Actions, GHCR |

---

## 5. Screenshots / UI Walkthrough

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  MERCADOINSIGHT   [ Licitaciones ]  [ Proveedores ]  [ Organismos ]  [ IA Chat ] [⚙️]  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  🔍 Búsqueda: "camas clínicas eléctricas"                 Región: Todas   Estado: Abierta│
├────────────────────────────────────────────────────────────────────────────────────────┤
│  KPIs Ejecutivos:                                                                      │
│  ┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐         │
│  │ Licitaciones Activas  │ │ Monto Total Estimado  │ │ Proveedores Activos   │         │
│  │ 1,420 (+12%)          │ │ $ 4.250.000.000 CLP   │ │ 348                   │         │
│  └───────────────────────┘ └───────────────────────┘ └───────────────────────┘         │
│                                                                                        │
│  Últimas Licitaciones Priorizadas por Scoring de Relevancia:                          │
│  ┌───────────────┬───────────────────────────┬──────────────┬──────────────┬─────────┐ │
│  │ Código        │ Título                    │ Organismo    │ Monto Est.   │ Score   │ │
│  ├───────────────┼───────────────────────────┼──────────────┼──────────────┼─────────┤ │
│  │ 1058-12-LR26  │ Adquisición Sillas Ruedas │ Senama RM    │ $ 45.000.000 │ 98% ⭐  │ │
│  │ 2234-05-LE26  │ Insumos Geriátricos Hosp. │ SS Concepción│ $ 82.000.000 │ 95% ⭐  │ │
│  │ 1402-22-L126  │ Servicio Apoyo Técnico    │ Senadis      │ $ 30.000.000 │ 89%     │ │
│  └───────────────┴───────────────────────────┴──────────────┴──────────────┴─────────┘ │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

Interfaces operativas detalladas documentadas en [docs/08-frontend/](docs/08-frontend/).

---

## 6. Installation

### Requisitos
- Docker Engine >= 26.0 y Docker Compose v2.
- Git >= 2.40.

### Clonar y Configurar
```bash
git clone https://github.com/ernestostarck/market-insight.git
cd market-insight
cp .env.example .env
```

---

## 7. Development

### Paso 1: Levantar Bases de Datos (PostgreSQL & Redis)
Asegúrate de tener Docker corriendo e inicia los contenedores de datos:
```bash
docker compose up -d postgres redis
```

### Paso 2: Encender el Backend (FastAPI)
Abre una terminal en la raíz del proyecto:
```bash
cd apps/backend
..\..\.venv\Scripts\activate          # En Windows
# source ../../.venv/bin/activate     # En Linux / macOS

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- API & Swagger UI disponible en: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- Healthcheck: [http://localhost:8000/health/ready](http://localhost:8000/health/ready)

### Paso 3: Encender el Frontend (React)
Abre una segunda terminal:
```bash
cd apps/frontend
npm run dev
```
- Aplicación web disponible en: [http://localhost:5173](http://localhost:5173)

### Paso 4: Iniciar Sesión en la Plataforma
Ingresa a [http://localhost:5173/login](http://localhost:5173/login) con tu cuenta. El registro
público está deshabilitado: las cuentas las crea un administrador desde **Configuración → Usuarios**
(o con `python infrastructure/scripts/create-user.py --email <correo>`, que pide la contraseña sin
mostrarla). Nunca escribas contraseñas en este README ni en el código.

> [!NOTE]
> El frontend tiene configurado un proxy en `vite.config.ts` que redirige automáticamente todas las peticiones a `/api/*` hacia `http://localhost:8000`.

Guía extendida paso a paso en [docs/deployment/development.md](docs/deployment/development.md).

---

## 8. Testing

La plataforma cuenta con **54 tests automatizados** de backend, integración e infraestructura:

```bash
# Ejecutar todas las suites de prueba de backend e infraestructura
pytest apps/backend/tests/

# Pruebas unitarias de frontend
cd apps/frontend && npm run test:run

# Auditoría automatizada de seguridad
python infrastructure/scripts/security-audit.py
```

---

## 9. Deployment

El despliegue está automatizado mediante GitHub Actions hacia ambientes con aislamiento de red:
- **Staging**: [docs/deployment/staging.md](docs/deployment/staging.md)
- **Producción**: [docs/deployment/production.md](docs/deployment/production.md)
- **Reversión de Emergencia**: [docs/deployment/rollback.md](docs/deployment/rollback.md)
- **Recuperación ante Desastres**: [docs/deployment/disaster-recovery.md](docs/deployment/disaster-recovery.md) y [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md) (RPO $\le 1$h, RTO $\le 1$h).

---

## 10. API

FastAPI expone una API REST v1 estandarizada con OpenAPI 3.1:
- `POST /api/v1/auth/login`: Autenticación con JWT Bearer.
- `GET /api/v1/licitaciones`: Listados con paginación (`page`, `page_size`) y filtros facetados.
- `POST /api/v1/nlp/hybrid-search`: Búsqueda combinada (FTS + vector RRF).
- `POST /api/v1/chat/conversations/{id}/messages/stream`: Streaming en tiempo real (SSE) con citas factuales.
- `GET /health/ready`: Readiness probe para orquestadores.

Especificación completa en [API.md](API.md) y [docs/api/README.md](docs/api/README.md).

---

## 11. AI / RAG

La capa de inteligencia artificial desacopla el enriquecimiento asíncrono de la atención conversacional:
- **NLP**: Motor de reglas sobre taxonomía de 3 niveles, embeddings densos y clasificación híbrida con $F_1$ Macro de 90.5%.
- **Conversacional**: Planificador determinístico de consultas, generación Text-to-SQL de solo lectura y validación de fidelidad (*grounding score*).
- **Gobernanza**: Cost tracker por token y alertas en Prometheus (`ai-cost.yml`).

Documentación detallada en [docs/07-ai/](docs/07-ai/) y [docs/ai/rag.md](docs/ai/rag.md).

---

## 12. Data

- **Esquema `core`**: Datos canónicos normalizados de ChileCompra.
- **Esquema `knowledge`**: Representaciones vectoriales e inferencias semánticas.
- **Esquema `dw` / `marts`**: Modelo dimensional Kimball para analítica de alta velocidad.
- **Pipeline ETL**: Extracción, validación canónica, cuarentena de errores y deduplicación.

Documentación detallada en [docs/data/model.md](docs/data/model.md), [docs/data/etl.md](docs/data/etl.md) y [docs/data/data-quality.md](docs/data/data-quality.md).

---

## 13. Monitoring

Infraestructura de observabilidad unificada (Fase 8 + Fase 10):
- **Prometheus & Alertmanager**: Scraping de métricas de negocio, HTTP, BD, ETL y costos de IA.
- **Grafana**: 8 dashboards preconfigurados para SLOs, PostgreSQL, Redis, ETL, NLP, RAG y logs.
- **Loki & Sentry**: Agregación de logs JSON estructurados y rastreo de excepciones con release tracking.

Guía operativa en [docs/operations/monitoring.md](docs/operations/monitoring.md) y [docs/deployment/observability-final.md](docs/deployment/observability-final.md).

---

## 14. Security

- **Checklist de 18 Puntos**: Auditoría automatizada vía [security-audit.py](infrastructure/scripts/security-audit.py).
- **Redes Aisladas**: PostgreSQL, Redis y MinIO residen exclusivamente en `private-net`, sin puertos expuestos al host.
- **Guardrail SQL**: Rol de base de datos `ai_analyst` con permiso exclusivo `pg_read_all_data` y bloqueo de comandos destructivos.
- **Higiene de Secretos**: Exclusión estricta de credenciales en Git y `.dockerignore`.

Guía completa en [docs/deployment/security-audit.md](docs/deployment/security-audit.md) y [docs/deployment/network-architecture.md](docs/deployment/network-architecture.md).

---

## 15. Roadmap

| Fase | Área | Estado | Entregables Principales |
| :---: | :--- | :---: | :--- |
| **0** | Diseño y Arquitectura | ✅ | Definición de producto, requerimientos y Clean Architecture |
| **1** | Infraestructura Base | ✅ | Docker Compose, PostgreSQL 17, Redis 7, MinIO |
| **2** | Integración ChileCompra | ✅ | SDK tipado de cliente API y fuentes de datos abiertos |
| **3** | Motor ETL | ✅ | Ingesta incremental, validación, cuarentena y deduplicación |
| **4** | Data Warehouse | ✅ | Modelo dimensional Kimball, esquemas `dw` y `marts` |
| **5** | Backend API | ✅ | Endpoints FastAPI v1, autenticación JWT, paginación y filtros |
| **6** | Inteligencia NLP | ✅ | Taxonomía geriátrica, reglas léxicas, pgvector y NER |
| **7** | Dashboard React | ✅ | Single Page Application, ECharts, Leaflet y TanStack Query |
| **8** | Observabilidad | ✅ | Prometheus, Grafana, Alertmanager, Loki y Sentry |
| **9** | Conversational AI | ✅ | Motor RAG híbrido, Text-to-SQL de solo lectura y streaming SSE |
| **10** | Despliegue y Runbooks | 🔄 | CI/CD, red en dos niveles, backups SHA-256, RPO/RTO y documentación técnica |

---

## 16. License

Este proyecto está bajo la Licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más detalles.
