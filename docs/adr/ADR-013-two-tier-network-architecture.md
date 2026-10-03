# ADR-013: Aislamiento de Red en Dos Niveles (Public-Net y Private-Net)

- **Status**: Aceptado
- **Fecha**: 2026-09-20
- **Decisores**: Equipo de Seguridad e Infraestructura

---

## Contexto
Uno de los mayores riesgos en aplicaciones basadas en Docker Compose es la exposición accidental de motores de bases de datos o almacenamiento hacia la interfaz pública del host (`0.0.0.0:5432`, `0.0.0.0:6379`, `0.0.0.0:9000`), permitiendo escaneos y ataques de fuerza bruta directos desde Internet.

## Decisión
Segmentar los contenedores en dos redes virtuales independientes gestionadas por Docker:
1. **`public-net`**: Red expuesta externamente. Únicamente el proxy inverso NGINX publica los puertos `80/tcp` y `443/tcp`.
2. **`private-net`**: Red interna totalmente aislada sin directivas `ports:` mapeadas al host. PostgreSQL, Redis, MinIO y Celery Workers residen exclusivamente aquí. Los servicios Backend, Grafana y Alertmanager actúan como puentes entre ambas redes.

## Alternativas Consideradas
1. **Red Única Plana por Defecto (`bridge` de Docker Compose)**: Todos los servicios se comunican sin restricción. Si un contenedor se ve comprometido o un desarrollador añade un mapeo `ports: - "5432:5432"` por error, la base de datos queda inmediatamente expuesta al mundo.
2. **Overlay Networks con Cifrado IPSec (Docker Swarm)**: Máxima seguridad cifrada, pero introduce complejidad de orquestación innecesaria para un host productivo único.

## Consecuencias
- **Positivas**:
  - Imposibilidad de conectar directamente a PostgreSQL o Redis desde fuera del servidor sin un túnel SSH autenticado o VPN.
  - La superficie de ataque exterior se reduce al puerto `443/tcp` de NGINX con TLS y WAF.
- **Negativas**:
  - Para administración manual o depuración desde el equipo local, el administrador debe usar un túnel SSH (`ssh -L 5432:localhost:5432`) o `docker exec`.
