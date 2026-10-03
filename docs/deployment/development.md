# Guía de Entorno de Desarrollo — Local Setup

Esta guía detalla los pasos para configurar, ejecutar y depurar el entorno local de desarrollo de **MercadoInsight**.

---

## 1. Requisitos Previos

- **Sistema Operativo**: Linux, macOS o Windows (con WSL2 recomendado).
- **Docker & Docker Compose**: Docker Engine >= 26.0 y Docker Compose v2.
- **Python**: 3.13 o 3.14 con gestor de entornos virtuales (`venv` o `uv`).
- **Node.js**: >= 20.x con `npm` >= 10.x.
- **Git**: >= 2.40.

---

## 2. Configuración Inicial

### 2.1 Clonar el Repositorio
```bash
git clone https://github.com/ernestostarck/market-insight.git
cd market-insight
```

### 2.2 Variables de Entorno
Copiar el archivo de plantilla para desarrollo:
```bash
cp .env.example .env
```

Asegurar las siguientes variables en `.env`:
```ini
ENVIRONMENT=development
DEBUG=True
SECRET_KEY=dev_secret_key_mercado_insight_minimum_32_chars_ok!
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=market_insight
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/market_insight
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
OPENAI_API_KEY=mock-key-or-real-for-ai-dev
```

### 2.3 Certificados TLS Locales
Generar certificados autofirmados para pruebas HTTPS locales:
```bash
python infrastructure/scripts/generate-dev-certs.py
```

---

## 3. Ejecución del Entorno

### Opción A: Stack Completo con Docker Compose (Recomendado)
```bash
docker compose -f docker/compose/docker-compose.yml up -d
```

Servicios accesibles localmente:
- **Frontend SPA**: `http://localhost:5173` (o `https://localhost` vía NGINX)
- **FastAPI Backend**: `http://localhost:8000` (Swagger UI: `http://localhost:8000/api/docs`)
- **MinIO Console**: `http://localhost:9001`
- **Grafana**: `http://localhost:3000` (admin/admin)
- **Prometheus**: `http://localhost:9090`

### Opción B: Desarrollo Híbrido (Infraestructura en Docker + Código en Host)

1. **Iniciar únicamente bases de datos y colas**:
   ```bash
   docker compose -f docker/compose/docker-compose.yml up -d postgres redis minio
   ```

2. **Iniciar Backend en modo Hot-Reload**:
   ```bash
   cd apps/backend
   python -m venv .venv
   source .venv/bin/activate  # En Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   alembic upgrade head
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Iniciar Celery Worker**:
   ```bash
   cd apps/backend
   celery -A app.worker.celery_app worker --loglevel=info -Q default,etl,nlp,ai
   ```

4. **Iniciar Frontend**:
   ```bash
   cd apps/frontend
   npm install
   npm run dev
   ```

---

## 4. Ejecución de Tests en Desarrollo

```bash
# Backend unit & integration tests
cd apps/backend
pytest -v

# Frontend unit tests
cd apps/frontend
npm run test:run

# Auditoría de seguridad local
python infrastructure/scripts/security-audit.py
```
