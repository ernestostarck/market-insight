# Guía Operativa de Alertmanager y Gestión de Alertas

## 1. Arquitectura de Alertas
El sistema de monitoreo de **MercadoInsight** canaliza alertas generadas por Prometheus hacia **Alertmanager**:

```
+------------------------------------+
|  Prometheus Rules & Evaluator      |
|  (/etc/prometheus/rules/*.yml)     |
+-----------------+------------------+
                  |
                  | alerts (HTTP /api/v2/alerts)
                  v
+-----------------+------------------+
|          Alertmanager              |
|  - Deduplicación                   |
|  - Agrupación (alertname, service) |
|  - Inhibición (critical -> warning)|
|  - Enrutamiento por severidad      |
+--------+--------+--------+---------+
         |        |        |
         |        |        +---> [info] solo log (webhook de la API)
         |        +------------> [warning] email + webhook de la API
         +---------------------> [critical] email + webhook de la API

Webhook de la API: POST /api/v1/monitoring/alerts/webhook -> una línea de log JSON por alerta
(event="alert_notification", visible en Loki) y el contador alertmanager_notifications_received_total.
Producción lo autentica con ALERT_WEBHOOK_TOKEN; nginx no lo expone.
```

---

## 2. Configuración de Tiempos y Agrupación
- **Group Wait (`group_wait: 30s`)**: Tiempo de espera inicial para agrupar alertas similares antes de enviar la primera notificación.
- **Group Interval (`group_interval: 5m`)**: Intervalo para enviar nuevas notificaciones de alertas agregadas al mismo grupo.
- **Repeat Interval (`repeat_interval: 12h`)**: Período de retransmisión de alertas que continúan activas y sin resolver.

---

## 3. Reglas de Inhibición
Mientras una alerta `critical` de un equipo (`team`) esté activa, las `warning` del mismo equipo se inhiben (primero la causa raíz). Ejemplo: `ETLFailed` inhibe `DataFreshnessWarning`.

## 3.1 Pruebas

- `make alert-tests`: tests unitarios de cada regla con `promtool` (dispara ante una falla controlada y no dispara con la plataforma sana).
- `make test-env`: además verifica, con un Alertmanager real, la entrega al webhook, la deduplicación y el silenciamiento.

---

## 4. Gestión de Silencios (Silences)

### 4.1 Vía Web UI de Alertmanager
1. Acceder a `http://localhost:9093/#/silences` (o endpoint configurado de Alertmanager).
2. Hacer clic en **"New Silence"**.
3. Definir los matchers (ej. `alertname="DataFreshnessExceeded"`, `service="mercado-publico-etl"`).
4. Definir duración estimada (inicio y fin de ventana de mantenimiento).
5. Ingresar autor y comentario justificando el silencio (ej. *"Mantenimiento programado API ChileCompra"*).
6. Confirmar la creación.

### 4.2 Vía CLI (`amtool`)
Para silenciar alertas desde scripts o terminal utilizando `amtool`:
```bash
# Crear un silencio de 2 horas para un servicio en mantenimiento
amtool silence add alertname="HighErrorRate" service="market-insight-backend" \
  --duration=2h \
  --comment="Despliegue de actualización de versión" \
  --author="devops-team" \
  --alertmanager.url="http://localhost:9093"

# Listar silencios activos
amtool silence query --alertmanager.url="http://localhost:9093"

# Expirar/eliminar un silencio
amtool silence expire <SILENCE_ID> --alertmanager.url="http://localhost:9093"
```

---

## 5. Prueba de Alerta Sintética (Synthetic Test)
Para validar el pipeline completo Prometheus -> Alertmanager -> Receptores sin provocar un fallo real:

```bash
# Enviar alerta de prueba directamente a Alertmanager v2 API:
curl -X POST http://localhost:9093/api/v2/alerts \
  -H "Content-Type: application/json" \
  -d '[
    {
      "labels": {
        "alertname": "TestSyntheticAlert",
        "service": "monitoring-test",
        "severity": "warning",
        "environment": "development"
      },
      "annotations": {
        "summary": "Prueba sintética de Alertmanager",
        "description": "Verificación del flujo de recepción y enrutamiento de notificaciones"
      },
      "startsAt": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
      "endsAt": "'$(date -u -d "+10 minutes" +"%Y-%m-%dT%H:%M:%SZ")'"
    }
  ]'
```
Verifique la recepción en el dashboard de Alertmanager en `http://localhost:9093` y en los registros del webhook.
