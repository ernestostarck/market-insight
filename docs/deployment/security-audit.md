# Auditoría de Seguridad y Hardening Final — MercadoInsight

Este documento detalla la lista de verificación completa, controles perimetrales, validaciones de seguridad de datos y ejecución del script de auditoría de seguridad para **MercadoInsight** (Fase 10.19).

---

## 1. Checklist Integral de Seguridad

| Control | Estado | Evidencia y Mecanismo de Control |
| :--- | :---: | :--- |
| **HTTPS Obligatorio** | ✅ Verificado | Redirección 301 en puerto 80, TLS 1.2/1.3, ciphers modernos y HSTS en [`default.conf`](file:///c:/Users/artut/market-insight/docker/nginx/prod/conf.d/default.conf). |
| **Secretos Fuera de Git** | ✅ Verificado | Reglas en `.gitignore` y `.dockerignore` (`.env`, `*.key`, `*.pem`, `*.dump`), validación con `validate-env.py`. |
| **CORS Restringido** | ✅ Verificado | Orígenes controlados por `BACKEND_CORS_ORIGINS`, sin comodines universales (`*`) en producción. |
| **Rate Limiting** | ✅ Verificado | Perimetral en NGINX (`api_limit` 25 r/s, `chat_limit` 5 r/s) y en FastAPI (`RateLimitMiddleware`). |
| **Autenticación JWT** | ✅ Verificado | Tokens HMAC-SHA256 con expiración breve (60 min), secretos robustos verificados y rotación. |
| **Autorización (RBAC)** | ✅ Verificado | Control de acceso por roles (`admin`, `analyst`, `viewer`) verificado a nivel de endpoints. |
| **SQL Read-Only para IA** | ✅ Verificado | Expresiones regulares en [`sql_retriever.py`](file:///c:/Users/artut/market-insight/apps/backend/app/ai/sql_retriever.py) que bloquean terminantemente `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`. |
| **PostgreSQL Aislado** | ✅ Verificado | `ports: !reset []` en compose prod; accesible exclusivamente desde la red interna privada. |
| **Redis Aislado** | ✅ Verificado | `ports: !reset []` en compose prod; protegido por contraseña fuerte (`requirepass`) en red privada. |
| **MinIO Aislado** | ✅ Verificado | `ports: !reset []` en compose prod; consola y API S3 confinadas en red interna privada. |
| **Prometheus Protegido** | ✅ Verificado | `ports: !reset []` en compose prod; sin exposición externa, consultado solo por Grafana internamente. |
| **Grafana Protegido** | ✅ Verificado | Enrutado mediante NGINX `/grafana/` protegido con HTTP Basic Auth y deshabilitación de login anónimo. |
| **Alertmanager Protegido** | ✅ Verificado | Enrutado mediante NGINX `/alertmanager/` protegido con HTTP Basic Auth y tokens compartidos. |
| **DEBUG=False en Prod** | ✅ Verificado | Forzado a `False` en `docker-compose.prod.yml` y validado por `validate-env.py`. |
| **Cabeceras de Seguridad** | ✅ Verificado | `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy`. |
| **Validación de Input/Output** | ✅ Verificado | Pydantic v2 en todas las rutas de API y sanitización de prompts en guardrails de IA. |
| **Escaneo de Dependencias** | ✅ Verificado | `bandit` y `pip-audit` en Python, `npm audit` en Node.js integrados al pipeline de CI. |
| **Escaneo de Contenedores** | ✅ Verificado | Trivy escanea imágenes Docker y filesystem con bloqueo por `CRITICAL,HIGH` en `security.yml`. |

---

## 2. Script de Auditoría Automatizada: `security-audit.py`

Se dispone del script oficial [`infrastructure/scripts/security-audit.py`](file:///c:/Users/artut/market-insight/infrastructure/scripts/security-audit.py) para auditar de forma desatendida las políticas perimetrales:

```bash
python infrastructure/scripts/security-audit.py
```

### Salida de Auditoría Exitosa
```text
[INFO] Starting MercadoInsight automated security audit ...
[INFO] [PASS] Secret Hygiene (.gitignore excludes sensitive files)
[INFO] [PASS] Docker Secret Hygiene (.dockerignore excludes env/certs)
[INFO] [PASS] Internal Port Isolation (PostgreSQL, Redis, MinIO, Prometheus not exposed)
[INFO] [PASS] AI SQL Read-Only Guardrails (DML/DDL blocked in sql_retriever.py)
[INFO] [PASS] NGINX Security Headers (HSTS, nosniff, SAMEORIGIN, Referrer-Policy)
[INFO] [PASS] Rate Limiting Enforced (RATE_LIMIT_ENABLED=true in production)
[INFO] [PASS] CORS Origin Restricted (No open wildcard in production)
[INFO] Security audit finished: 7 passed, 0 failed.
[INFO] All security controls VERIFIED successfully.
```

---

## 3. Matriz de Exposición de Puertos en Producción

| Servicio | Puerto Contenedor | Puerto Host (Producción) | Acceso Permitido |
| :--- | :--- | :--- | :--- |
| **nginx** | 80 / 443 | `0.0.0.0:80`, `0.0.0.0:443` | **Público (Internet)** |
| **frontend** | 80 | *Ninguno* (`ports: !reset []`) | Solo NGINX (`public-net`) |
| **backend** | 8000 | *Ninguno* (`ports: !reset []`) | NGINX (`public-net`) y Workers (`private-net`) |
| **postgres** | 5432 | *Ninguno* (`ports: !reset []`) | Solo Backend y Workers (`private-net`) |
| **redis** | 6379 | *Ninguno* (`ports: !reset []`) | Solo Backend y Workers (`private-net`) |
| **minio** | 9000 / 9001 | *Ninguno* (`ports: !reset []`) | Solo Backend y Workers (`private-net`) |
| **prometheus** | 9090 | *Ninguno* (`ports: !reset []`) | Solo Grafana (`private-net`) |
| **grafana** | 3000 | *Ninguno* (`ports: !reset []`) | Solo NGINX con Basic Auth |
| **alertmanager**| 9093 | *Ninguno* (`ports: !reset []`) | Solo NGINX con Basic Auth y Prometheus |
| **loki** | 3100 | *Ninguno* (`ports: !reset []`) | Solo Grafana y Promtail (`private-net`) |
