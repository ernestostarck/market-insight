# Escaneo de Seguridad y Contenedores — MercadoInsight

Este documento detalla la política, herramientas y flujos de escaneo de seguridad estática y de contenedores ejecutados por el workflow [`security.yml`](file:///c:/Users/artut/market-insight/.github/workflows/security.yml).

---

## 1. Alcance de Seguridad

La estrategia de escaneo de seguridad en MercadoInsight abarca tres niveles complementarios:

1. **Detección de Secretos y Misconfiguraciones**: Búsqueda activa de credenciales hardcodeadas, claves privadas, tokens y configuraciones inseguras de Docker/NGINX en el repositorio.
2. **Escaneo de Vulnerabilidades en Imágenes Docker (Trivy)**: Análisis exhaustivo de los paquetes del sistema operativo base (Debian Slim, Alpine Linux) y de las librerías instaladas en las capas de los contenedores productivos.
3. **Auditoría de Dependencias de Lenguaje**: Verificación de CVEs en librerías Python (`pip-audit`) y paquetes npm (`npm audit`).

---

## 2. Integración con Trivy

**Aqua Security Trivy** se integra en el pipeline de GitHub Actions como analizador de vulnerabilidades:

### 2.1 Escaneo de Sistema de Archivos y Secretos
```yaml
uses: aquasecurity/trivy-action@0.28.0
with:
  scan-type: 'fs'
  scan-ref: '.'
  ignore-unfixed: true
  format: 'sarif'
  output: 'trivy-fs-results.sarif'
  severity: 'CRITICAL,HIGH'
```
* Identifica archivos `.env` accidentales, claves privadas `.pem`/`.key` o tokens API en commits.
* Genera un reporte SARIF (Static Analysis Results Interchange Format) que se publica automáticamente en la pestaña **Security → Code scanning** de GitHub.

### 2.2 Escaneo de Imágenes de Contenedores
Para cada imagen construida ([Backend](file:///c:/Users/artut/market-insight/apps/backend/Dockerfile.prod) y [Frontend](file:///c:/Users/artut/market-insight/apps/frontend/Dockerfile.prod)):
```yaml
uses: aquasecurity/trivy-action@0.28.0
with:
  image-ref: 'mercadoinsight-backend:scan-target'
  format: 'table'
  exit-code: '1'
  ignore-unfixed: true
  vuln-type: 'os,library'
  severity: 'CRITICAL,HIGH'
```

---

## 3. Política de Bloqueo por Severidad

| Nivel de Severidad | Acción en Pipeline | Tiempo Máximo de Remediación (SLA) |
| :--- | :--- | :--- |
| **CRITICAL** | **Bloqueo Inmediato**: El workflow falla (`exit 1`), el PR no puede mergearse y el despliegue se aborta. | 24 horas |
| **HIGH** | **Bloqueo Inmediato**: Requiere actualización de la dependencia o base image antes de promover a producción. | 72 horas |
| **MEDIUM** | Notificación en el reporte de seguridad para actualización en la siguiente ventana de mantenimiento. | 14 días |
| **LOW** | Informativo en logs de CI. | Próximo release menor |

---

## 4. Escaneo Continuo Programado (Weekly Cron)

Dado que se descubren nuevas vulnerabilidades (CVEs) continuamente sobre software ya publicado, el workflow `security.yml` se ejecuta de manera autónoma todos los lunes a las **04:00 UTC** (`cron: '0 4 * * 1'`).

Esto garantiza que si una versión desplegada en producción contiene una librería en la que se divulga una vulnerabilidad post-despliegue, el equipo de ingeniería reciba una notificación inmediata en GitHub Security.

---

## 5. Ejecución Local de Escaneo con Trivy

Para escanear localmente antes de enviar un commit:

```bash
# Escanear el sistema de archivos local en busca de vulnerabilidades y secretos
trivy fs --severity CRITICAL,HIGH .

# Escanear imagen compilada de backend
docker build -f apps/backend/Dockerfile.prod -t backend:test apps/backend
trivy image --severity CRITICAL,HIGH backend:test

# Escanear imagen compilada de frontend
docker build -f apps/frontend/Dockerfile.prod -t frontend:test apps/frontend
trivy image --severity CRITICAL,HIGH frontend:test
```
