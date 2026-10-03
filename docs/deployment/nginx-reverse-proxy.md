# Arquitectura NGINX Reverse Proxy — MercadoInsight

Este documento describe la configuración, arquitectura de enrutamiento, rate limiting, soporte para streaming de IA y hardening de seguridad implementado en **NGINX** como punto de entrada perimetral de **MercadoInsight**.

---

## 1. Arquitectura de Enrutamiento Unificado

MercadoInsight utiliza una estrategia de **dominio único** para servir la interfaz gráfica (React SPA) y los servicios de backend (FastAPI REST API):

```text
                                HTTPS (:443)
                            mercadoinsight.cl
                                    │
                                    ▼
                          ┌──────────────────┐
                          │   NGINX Edge     │
                          └──────────────────┘
                                    │
           ┌────────────────────────┼────────────────────────┐
           │                        │                        │
           ▼                        ▼                        ▼
     Path: `/`               Path: `/api/`          Path: `/grafana/`
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│   Frontend SPA   │      │  FastAPI Backend │      │     Grafana      │
│  (NGINX Alpine)  │      │     (:8000)      │      │ (HTTP Basic Auth)│
└──────────────────┘      └──────────────────┘      └──────────────────┘
```

### Ventajas del Enrutamiento Bajo el Mismo Dominio
* **Cero Preflights CORS**: Al compartir origen (`https://mercadoinsight.cl`), las peticiones `GET`/`POST`/`PUT`/`DELETE` desde la SPA hacia `/api/` no requieren peticiones preflight `OPTIONS`, reduciendo la latencia de cada llamada en 30-100ms.
* **Certificado TLS Único**: No requiere certificados multidominio o comodín para operar la API básica.
* **Trazabilidad de Request-ID**: NGINX inyecta o preserva la cabecera `X-Request-ID`, propagándola uniformemente hacia FastAPI y los logs de auditoría.

---

## 2. Soporte para Streaming y SSE (Fase 9: IA Conversacional)

Las consultas al asistente de IA y RAG emiten respuestas en tiempo real mediante **Server-Sent Events (SSE)** o transferencias por fragmentos (`chunked transfer encoding`). Por defecto, NGINX almacena en búfer las respuestas del backend antes de enviarlas al cliente, lo que rompería la experiencia fluida de generación de texto.

### Configuración Específica en NGINX
En [`docker/nginx/prod/conf.d/default.conf`](file:///c:/Users/artut/market-insight/docker/nginx/prod/conf.d/default.conf), las rutas `~ ^/api/v1/(ai|chat)/` cuentan con parámetros optimizados:

```nginx
location ~ ^/api/v1/(ai|chat)/ {
  limit_req zone=chat_limit burst=10 nodelay;
  proxy_pass http://backend:8000;

  # Desactivación de buffers para Server-Sent Events (SSE)
  proxy_buffering off;
  proxy_cache off;
  chunked_transfer_encoding on;

  # Timeouts extendidos para respuestas analíticas de LLM
  proxy_read_timeout 300s;
  proxy_send_timeout 300s;
}
```

* `proxy_buffering off`: Transmite inmediatamente cada token o fragmento generado por el LLM hacia el navegador.
* `proxy_read_timeout 300s`: Permite que consultas complejas que involucran búsquedas híbridas vectoriales y múltiples razonamientos LLM no sean cortadas por el proxy.

---

## 3. Rate Limiting Perimetral

Para proteger la infraestructura contra ataques de denegación de servicio (DoS) o scraping abusivo de competidores, se configuran dos zonas en memoria:

1. **Zona Global de API (`api_limit`)**:
   - Tasa: `25r/s` (25 peticiones por segundo por dirección IP).
   - Ráfaga (`burst`): Hasta 50 peticiones simultáneas procesadas sin retardo (`nodelay`).
2. **Zona de Asistente IA y Autenticación (`chat_limit`)**:
   - Tasa: `5r/s` por IP para controlar el consumo de tokens y prevenir saturación del pool de inferencia.
   - Ráfaga: Hasta 10 peticiones.
3. **Código de Estado**: `429 Too Many Requests` devuelto inmediatamente ante excesos.

---

## 4. Caché de Assets Estáticos

Los archivos empaquetados por Vite (JavaScript, CSS, imágenes con hash en el nombre) se sirven con cabeceras de caché inmutable:

```nginx
location ~* \.(?:css|js|jpg|jpeg|gif|png|ico|svg|woff|woff2|ttf|eot)$ {
  proxy_pass http://frontend:80;
  expires 30d;
  add_header Cache-Control "public, max-age=2592000, immutable";
  access_log off;
}
```

Esto reduce drásticamente el consumo de CPU y ancho de banda en visitas recurrentes de usuarios.

---

## 5. Compresión Gzip

En [`docker/nginx/nginx.conf`](file:///c:/Users/artut/market-insight/docker/nginx/nginx.conf) se activa la compresión para reducir el tamaño de transferencia:
* `gzip_comp_level 6`: Balance óptimo entre compresión y uso de CPU.
* `gzip_min_length 256`: Respuestas menores a 256 bytes no se comprimen para evitar sobrecarga.
* Tipos comprimidos: `application/json`, `text/css`, `application/javascript`, `image/svg+xml`, `font/woff2`.

---

## 6. Endurecimiento de Seguridad Perimetral

### 6.1 Protección de Rutas Internas
NGINX bloquea de forma absoluta el acceso perimetral a endpoints de soporte que solo deben usarse dentro de la red privada Docker:
* `/metrics`: Retorna `403 Forbidden` (scrapeado únicamente por Prometheus en la red interna).
* `/api/v1/monitoring/alerts/webhook`: Retorna `403 Forbidden` (invocado únicamente por Alertmanager).

### 6.2 Cabeceras de Seguridad
* **HSTS**: `Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"` obliga a los navegadores a comunicarse exclusivamente por HTTPS durante al menos un año.
* **X-Content-Type-Options**: `nosniff` previene la reinterpretación de tipos MIME.
* **X-Frame-Options**: `SAMEORIGIN` previene ataques de Clickjacking.
* **Referrer-Policy**: `strict-origin-when-cross-origin`.
* **Content-Security-Policy**: Restringe orígenes de scripts y conexiones (`default-src 'self' ...`).
* **Permissions-Policy**: Deshabilita hardware innecesario (`camera=(), microphone=(), geolocation=()`).
