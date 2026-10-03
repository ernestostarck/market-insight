#!/bin/sh
set -eu

mc alias set mercadoinsight http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
mc mb --ignore-existing "mercadoinsight/${MINIO_BUCKET_PRIVATE_DOCUMENTS:-documents-private}"
mc mb --ignore-existing "mercadoinsight/${MINIO_BUCKET_PUBLIC_DOCUMENTS:-documents-public}"
mc mb --ignore-existing "mercadoinsight/${MINIO_BUCKET_ATTACHMENTS:-attachments}"
mc anonymous set download "mercadoinsight/${MINIO_BUCKET_PUBLIC_DOCUMENTS:-documents-public}"
