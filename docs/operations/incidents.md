# Marco de Gestión de Incidentes — Incident Management

Este documento establece el marco formal para la clasificación, respuesta, comunicación, escalamiento y post-mortem de incidentes operacionales en **MercadoInsight**.

---

## 1. Matriz de Severidad y Niveles de Servicio (SLA)

| Severidad | Definición | Ejemplo | Tiempo Máximo de Respuesta (MTTA) | Tiempo Objetivo de Mitigación (MTTR) |
| :---: | :--- | :--- | :---: | :---: |
| **P1 - Crítico** | Caída total de la plataforma o pérdida de integridad de datos. Afecta a todos los usuarios. | API no responde (`502 Bad Gateway`), base de datos caída, corrupción de almacenamiento. | **< 15 minutos** | **< 1 hora** (conforme a RTO) |
| **P2 - Alto** | Degradación severa de una funcionalidad crítica sin alternativa inmediata. | El Asistente RAG no responde, el pipeline ETL falló por más de 12 horas consecutivas. | **< 30 minutos** | **< 4 horas** |
| **P3 - Medio** | Falla parcial o cosmética en una funcionalidad secundaria; existen alternativas de trabajo. | Errores en la exportación a Excel, lentitud en dashboard secundario de analítica. | **< 2 horas** | **< 24 horas** |
| **P4 - Bajo** | Problemas menores de UI, errores tipográficos o consultas operativas. | Desalineación de un gráfico en pantalla ultrawide, warning en log sin impacto funcional. | **< 8 horas** | Próximo sprint de release |

---

## 2. Flujo de Respuesta ante Incidentes

```text
[ Detección (Alerta Prometheus / Sentry / Reporte) ]
                      │
                      ▼
[ 1. Triaje Inmediato y Asignación de Severidad (P1-P4) ]
                      │
                      ▼
[ 2. Declaración del Incidente en Canal #incidents ]
                      │
                      ▼
[ 3. Activación de Rol Incident Commander (IC) ]
                      │
                      ▼
[ 4. Diagnóstico y Ejecución de Runbook de Mitigación ]
                      │
                      ▼
[ 5. Verificación de Recuperación y Cierre de Alertas ]
                      │
                      ▼
[ 6. Redacción de Post-Mortem Blameless (< 48 horas) ]
```

---

## 3. Matriz de Escalamiento Operacional (On-Call)

Cuando un incidente no se mitiga dentro del tiempo objetivo (MTTA/MTTR):

1. **Nivel 1 (L1 - Monitoreo & Operaciones)**:
   - Recibe la alerta de Alertmanager / PagerDuty.
   - Ejecuta validaciones de salud preliminares (`curl /health/ready`, `docker ps`).
   - Si no se resuelve en 15 minutos para P1 o 30 minutos para P2, escala a L2.
2. **Nivel 2 (L2 - Especialistas Backend / Infraestructura / Datos)**:
   - Analiza trazas en Loki, conexiones en PostgreSQL, cuellos de botella en Redis o Celery.
   - Aplica runbooks específicos de [troubleshooting.md](troubleshooting.md).
   - Si requiere cambios mayores de arquitectura o restauración DR completa, escala a L3.
3. **Nivel 3 (L3 - Tech Lead / Arquitecto Principal)**:
   - Declara activación de Disaster Recovery si aplica.
   - Autoriza despliegues de emergencia o hotfixes en producción.

---

## 4. Canales de Comunicación y Notificación

- **Canal Interno de Emergencia**: `#incident-war-room` en Slack / Discord.
- **Canal de Estado para Usuarios / Stakeholders**: Página de estado (`status.mercadoinsight.cl`) y canal de anuncios.
- **Cadencia de Actualización durante P1**: Cada **20 minutos**, independientemente de si hay avances técnicos definitivos.

---

## 5. Plantilla de Post-Mortem Sin Culpas (Blameless Post-Mortem)

A completarse dentro de las 48 horas posteriores al cierre de un incidente P1 o P2:

```markdown
# Incidente Post-Mortem: [INC-YYYYMMDD-TITULO]

## Resumen Ejecutivo
- **Fecha y Hora**: YYYY-MM-DD HH:MM UTC
- **Duración Total**: X horas, Y minutos
- **Severidad**: P1 / P2
- **Impacto**: [Detalle de usuarios afectados, peticiones fallidas o datos no procesados]
- **Incident Commander**: [Nombre del responsable]

## Cronología de Eventos (Timeline)
- **14:02 UTC**: Se dispara alerta Prometheus `APIErrorRateHigh`.
- **14:08 UTC**: El ingeniero On-call confirma caída en `/health/ready`.
- **14:15 UTC**: Se identifica saturación de conexiones en PostgreSQL debido a query no indexada.
- **14:22 UTC**: Se reinicia el servicio backend y se ajusta el pool de conexiones.
- **14:30 UTC**: La tasa de errores retorna a 0%. Incidente mitigado.

## Causa Raíz (Root Cause - Los 5 Porqués)
1. ¿Por qué falló la API? Se agotaron las conexiones a PostgreSQL.
2. ¿Por qué se agotaron? Una consulta masiva bloqueó tablas sin índice.
3. ...

## Acciones Correctivas y Preventivas (Action Items)
- [ ] [P1] Agregar índice concurrente en campo X (Responsable: @backend - Plazo: 2 días)
- [ ] [P2] Reducir timeout de consultas en FastAPI a 5 segundos (Responsable: @devops - Plazo: 3 días)
- [ ] [P3] Mejorar alerta de umbral de conexiones al 80% (Responsable: @infra - Plazo: 1 semana)
```
