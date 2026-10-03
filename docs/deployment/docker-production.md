# Arquitectura de Contenedores de Producción — MercadoInsight

Este documento detalla la ingeniería de contenedores Docker de producción para **MercadoInsight**, orientada a maximizar la seguridad, reducir la superficie de ataque, garantizar reproducibilidad determinista y optimizar el tamaño de las imágenes finales mediante **multi-stage builds**.

---

## 1. Principios de Empaquetado en Producción

1. **Separación Estricta Builder / Runtime**:
   - Todo compilador (`gcc`, `g++`, `make`), encabezados de desarrollo (`python-dev`, `libpq-dev`) y herramientas de build residen exclusivamente en la fase transitoria de compilación (`builder`).
   - La imagen final de producción (`runtime`) contiene únicamente los binarios interpretados y bibliotecas compartidas estrictamente necesarias para la ejecución.
2. **Ejecución como Usuario No-Root**:
   - Ni la API de FastAPI ni los Celery workers se ejecutan como `root`.
   - Se crea y asigna un usuario del sistema sin privilegios (`appuser`, UID/GID `10001`) con shell deshabilitada (`/bin/false`) y permisos mínimos sobre los archivos de aplicación.
3. **Instalación Determinista**:
   - Backend: Las dependencias de desarrollo (`pytest`, `ruff`, etc.) se desinstalan o excluyen de la imagen productiva.
   - Frontend: Se utiliza `npm ci` en lugar de `npm install` para garantizar coincidencia exacta con `package-lock.json`.
4. **Healthchecks Nativos en Imagen**:
   - Cada contenedor define una directiva `HEALTHCHECK` que permite al Docker daemon y a balanceadores perimetrales monitorear el estado real del proceso sin scripts externos.
5. **Cero Secretos en Capas**:
   - Gracias a [`.dockerignore`](file:///c:/Users/artut/market-insight/.dockerignore), ningún archivo `.env`, certificado privado, ni clave SSH entra en el contexto de construcción (`build context`).

---

## 2. Backend API (`apps/backend/Dockerfile.prod`)

### 2.1 Diagrama de Construcción

```text
┌────────────────────────────────────────────────────────┐
│ Stage 1: Builder (python:3.13-slim)                   │
│  ├── apt install build-essential curl                  │
│  ├── python -m venv /opt/venv                         │
│  ├── pip install . (wheels compilados)                 │
│  └── pip uninstall pytest, ruff                       │
└────────────────────────────────────────────────────────┘
                           │
             Copia solo    │  /opt/venv
             el entorno    ▼
┌────────────────────────────────────────────────────────┐
│ Stage 2: Runtime (python:3.13-slim)                    │
│  ├── apt install curl (solo para healthcheck)          │
│  ├── useradd appuser (UID 10001)                       │
│  ├── COPY --chown=appuser /opt/venv                    │
│  ├── COPY --chown=appuser app, alembic                 │
│  ├── USER appuser                                      │
│  └── CMD ["uvicorn", "--workers", "4", ...]            │
└────────────────────────────────────────────────────────┘
```

### 2.2 Directivas Clave
* **Usuario**: `appuser:appgroup` (UID `10001`).
* **Healthcheck**:
  ```dockerfile
  HEALTHCHECK --interval=15s --timeout=5s --retries=3 --start-period=10s \
      CMD curl -f http://localhost:8000/health/live || exit 1
  ```
* **Comando Productivo**:
  Uvicorn con 4 procesos workers (`--workers 4`) para maximizar la concurrencia en CPUs multinúcleo y respetar cabeceras proxy (`--proxy-headers --forwarded-allow-ips *`).

---

## 3. Celery Workers (`apps/backend/Dockerfile.worker.prod`)

Utilizado por los servicios de tareas asíncronas de NLP y ETL:
* **Base compartida**: Reutiliza la misma base virtualenv optimizada de Python 3.13.
* **Healthcheck específico de Celery**:
  ```dockerfile
  HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=20s \
      CMD celery -A app.worker.celery_app:celery_app inspect ping -t 5 || exit 1
  ```
  Esto valida que el worker esté conectado al broker Redis y responda al comando ping antes de recibir tareas productivas.

---

## 4. Frontend SPA (`apps/frontend/Dockerfile.prod`)

### 4.1 Diagrama de Construcción

```text
┌────────────────────────────────────────────────────────┐
│ Stage 1: Build (node:20-alpine)                       │
│  ├── COPY package.json package-lock.json               │
│  ├── RUN npm ci (reproducible y bloqueado)             │
│  ├── COPY . .                                          │
│  └── RUN npm run build (genera /dist)                  │
└────────────────────────────────────────────────────────┘
                           │
             Copia solo    │  /app/frontend/dist
             los estáticos ▼
┌────────────────────────────────────────────────────────┐
│ Stage 2: Runtime (nginx:1.27-alpine)                   │
│  ├── COPY dist /usr/share/nginx/html                   │
│  ├── COPY nginx.conf /etc/nginx/conf.d/default.conf    │
│  ├── HEALTHCHECK wget -q --spider http://localhost:80/ │
│  └── CMD ["nginx", "-g", "daemon off;"]                │
└────────────────────────────────────────────────────────┘
```

### 4.2 Ventajas de la Separación
* **Node.js ausente en producción**: Ni Node.js ni `npm` residen en el contenedor que sirve la aplicación al usuario.
* **Tamaño reducido**: La imagen pasa de ~600MB (con Node.js y dependencias `devDependencies`) a menos de **45MB** (NGINX Alpine con archivos estáticos compilados).
* **Superficie de vulnerabilidades**: Al no haber intérprete de JavaScript en el host de runtime, se mitigan vectores de ataque basados en dependencias de desarrollo.

---

## 5. Matriz de Optimización y Seguridad

| Servicio | Dockerfile | Usuario | Base Builder | Base Runtime | Healthcheck |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Backend API** | `Dockerfile.prod` | `appuser` (10001) | `python:3.13-slim` | `python:3.13-slim` | `curl /health/live` |
| **NLP Worker** | `Dockerfile.worker.prod` | `appuser` (10001) | `python:3.13-slim` | `python:3.13-slim` | `celery inspect ping` |
| **ETL Worker** | `Dockerfile.worker.prod` | `appuser` (10001) | `python:3.13-slim` | `python:3.13-slim` | `celery inspect ping` |
| **Frontend** | `Dockerfile.prod` | `nginx` | `node:20-alpine` | `nginx:1.27-alpine` | `wget :80/` |

---

## 6. Comandos de Compilación y Validación

Para compilar las imágenes productivas localmente:
```bash
# Backend API
docker build -f apps/backend/Dockerfile.prod -t mercadoinsight-backend:latest apps/backend

# Celery Workers
docker build -f apps/backend/Dockerfile.worker.prod -t mercadoinsight-worker:latest apps/backend

# Frontend
docker build -f apps/frontend/Dockerfile.prod -t mercadoinsight-frontend:latest apps/frontend
```
