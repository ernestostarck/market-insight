# ADR-009: Uso de MinIO como Almacén de Objetos S3 Compatible

- **Status**: Aceptado
- **Fecha**: 2026-09-14
- **Decisores**: Equipo de Infraestructura y Datos

---

## Contexto
MercadoInsight debe almacenar documentos adjuntos de compras públicas (PDFs de bases técnicas, resoluciones, anexos económicos), respaldos del sistema y payloads crudos. Almacenar binarios pesados dentro de PostgreSQL (`BYTEA`) degrada el rendimiento de la base de datos, incrementa el tamaño de los checkpoints e infla los backups.

## Decisión
Desplegar **MinIO** como almacén de objetos autoalojado compatible con la API estándar de **AWS S3**.

## Alternativas Consideradas
1. **Sistema de Archivos Local (Bind Mount / Directorio en Disco)**: Extremadamente simple al inicio, pero carece de control de acceso granular por buckets, no soporta generación de URLs prefirmadas con expiración y complica la migración hacia nubes públicas.
2. **AWS S3 / Google Cloud Storage Directo**: Excelente servicio gestionado, pero introduce costos variables desde el día uno y dependencias de conectividad externa en entornos de desarrollo local y testing.

## Consecuencias
- **Positivas**:
  - **Portabilidad 100% S3**: El código de la aplicación usa `boto3` o el SDK oficial de S3 sin cambios si en el futuro se migra a AWS S3 o Cloudflare R2.
  - **Descargas Seguras**: Soporte nativo para URLs prefirmadas temporales (`presigned URLs`) para que los usuarios descarguen bases sin exponer el storage públicamente.
  - **Aislamiento de Almacenamiento**: La base de datos PostgreSQL solo guarda metadatos y rutas, manteniendo su tamaño ágil.
- **Negativas**:
  - Requiere incluir los volúmenes de MinIO en la estrategia de respaldos periódicos (`backup.py`).
