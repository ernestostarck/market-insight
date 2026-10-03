# Configuración y Gestión de HTTPS / TLS — MercadoInsight

Este documento establece la arquitectura de transporte seguro, los estándares criptográficos, el procedimiento de emisión y renovación con **Let's Encrypt / Certbot**, y las herramientas de pruebas locales para **MercadoInsight**.

---

## 1. Estándares Criptográficos TLS

MercadoInsight aplica las directrices de seguridad de **Mozilla Intermediate TLS Configuration**, garantizando compatibilidad universal con clientes modernos y máxima resistencia ante vulnerabilidades criptográficas:

* **Protocolos Habilitados**: `TLSv1.2` y `TLSv1.3`.
* **Protocolos Inseguros Prohibidos**: `SSLv2`, `SSLv3`, `TLSv1.0`, `TLSv1.1` están completamente deshabilitados.
* **Ciphers Habilitados**:
  ```text
  ECDHE-ECDSA-AES128-GCM-SHA256
  ECDHE-RSA-AES128-GCM-SHA256
  ECDHE-ECDSA-AES256-GCM-SHA384
  ECDHE-RSA-AES256-GCM-SHA384
  ECDHE-ECDSA-CHACHA20-POLY1305
  ECDHE-RSA-CHACHA20-POLY1305
  DHE-RSA-AES128-GCM-SHA256
  DHE-RSA-AES256-GCM-SHA384
  ```
* **Optimización de Sesión**:
  - `ssl_session_cache shared:SSL:10m;` (permite reutilizar parámetros de sesión y acelerar handshakes subsecuentes).
  - `ssl_session_timeout 1d;`
  - `ssl_session_tickets off;` (previene ataques de forward secrecy basados en claves de tickets estáticas).

---

## 2. Redirección HTTP a HTTPS

El servidor NGINX expone el puerto `80` exclusivamente para dos propósitos:
1. **Desafío ACME Let's Encrypt**: Atiende la ruta `/.well-known/acme-challenge/` para validación de dominio.
2. **Sondeo de Liveness**: Atiende `/health` para chequeos no cifrados de balanceadores de carga internos.
3. **Redirección Permanente (301)**: Cualquier otra petición se redirige inmediatamente a `https://$host$request_uri`.

---

## 3. Emisión y Renovación con Let's Encrypt

### 3.1 Emisión Inicial (Certbot Webroot)
En el servidor de producción con NGINX en ejecución:

```bash
sudo certbot certonly \
    --webroot \
    --webroot-path /var/www/certbot \
    -d mercadoinsight.cl \
    -d www.mercadoinsight.cl \
    --agree-tos \
    --email admin@mercadoinsight.cl \
    --no-eff-email
```

Luego de emitidos, se enlazan o copian al directorio de certificados montado por Docker:
```bash
cp /etc/letsencrypt/live/mercadoinsight.cl/fullchain.pem docker/nginx/certs/fullchain.pem
cp /etc/letsencrypt/live/mercadoinsight.cl/privkey.pem docker/nginx/certs/privkey.pem
chmod 644 docker/nginx/certs/fullchain.pem
chmod 600 docker/nginx/certs/privkey.pem
```

### 3.2 Renovación Automática Desatendida
Se utiliza el script [`infrastructure/scripts/renew-certificates.sh`](file:///c:/Users/artut/market-insight/infrastructure/scripts/renew-certificates.sh).

Para programar la renovación automática en el host, configure una tarea en `cron` o un `systemd timer`:

```bash
# Editar crontab del root
sudo crontab -e

# Ejecutar chequeo de renovación todos los días a las 03:00 AM
0 3 * * * /opt/mercadoinsight/infrastructure/scripts/renew-certificates.sh >> /var/log/certbot-renew.log 2>&1
```

El script ejecuta `certbot renew` y, si los certificados cambiaron, recarga NGINX en caliente con `nginx -s reload` sin interrumpir las conexiones activas.

---

## 4. Certificados para Desarrollo y Staging

Para pruebas locales con HTTPS o despliegues de staging donde no se cuenta con un dominio público validable por Let's Encrypt, se utiliza el generador automatizado:

```bash
# Generar certificados autofirmados con SANs para mercadoinsight.cl, staging y localhost
python infrastructure/scripts/generate-dev-certs.py --output-dir docker/nginx/certs --domain mercadoinsight.cl
```

Este script genera certificados X.509 de 2048 bits con extensiones SAN para:
- `mercadoinsight.cl`
- `www.mercadoinsight.cl`
- `staging.mercadoinsight.cl`
- `localhost`
- `127.0.0.1`

---

## 5. Procedimientos de Validación

### 5.1 Validación vía CLI con cURL
```bash
# Verificar redirección 301 de HTTP a HTTPS
curl -I http://localhost/

# Verificar terminación TLS en puerto 443 (ignora verificación de CA si es autofirmado)
curl -k -I https://localhost/health

# Verificar que la versión mínima de TLS sea 1.2
curl -k -v --tlsv1.2 --tls-max 1.2 https://localhost/

# Verificar que TLS 1.0 sea rechazado
curl -k -v --tlsv1.0 --tls-max 1.0 https://localhost/ || echo "TLS 1.0 rechazado correctamente"
```

### 5.2 Validación en Producción con SSL Labs
Una vez desplegado con dominio público y DNS activo, el dominio debe evaluarse en [Qualys SSL Labs](https://www.ssllabs.com/ssltest/) para certificar una calificación **A+**.
