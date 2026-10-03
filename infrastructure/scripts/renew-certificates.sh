#!/usr/bin/env bash
# ==============================================================================
# MercadoInsight - Let's Encrypt Certificate Renewal Script
# ==============================================================================
# Run as a daily/weekly cron job or systemd timer:
#   0 3 * * * /path/to/renew-certificates.sh >> /var/log/certbot-renew.log 2>&1

set -euo pipefail

DOMAIN="${1:-mercadoinsight.cl}"
WEBROOT_DIR="/var/www/certbot"
CERTS_DIR="docker/nginx/certs"

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Starting Let's Encrypt certificate renewal check for ${DOMAIN}..."

if ! command -v certbot >/dev/null 2>&1; then
    echo "[ERROR] certbot binary not found on host. Please install certbot." >&2
    exit 1
fi

# Execute non-interactive renewal
certbot renew \
    --webroot \
    --webroot-path "${WEBROOT_DIR}" \
    --quiet \
    --agree-tos \
    --deploy-hook "
        echo '[$(date -u +\"%Y-%m-%dT%H:%M:%SZ\")] Certificates renewed successfully. Copying to ${CERTS_DIR}...';
        cp /etc/letsencrypt/live/${DOMAIN}/fullchain.pem ${CERTS_DIR}/fullchain.pem;
        cp /etc/letsencrypt/live/${DOMAIN}/privkey.pem ${CERTS_DIR}/privkey.pem;
        chmod 644 ${CERTS_DIR}/fullchain.pem;
        chmod 600 ${CERTS_DIR}/privkey.pem;
        echo '[$(date -u +\"%Y-%m-%dT%H:%M:%SZ\")] Reloading NGINX configuration...';
        docker compose exec -T nginx nginx -s reload || docker compose -f docker-compose.yml -f docker/compose/docker-compose.prod.yml exec -T nginx nginx -s reload;
    "

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Certificate renewal check completed."
