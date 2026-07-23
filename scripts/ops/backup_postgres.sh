#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${FORGEML_COMPOSE_FILE:-infra/compose/docker-compose.yml}"
BACKUP_DIR="${FORGEML_BACKUP_DIR:-backups/postgres}"
POSTGRES_USER="${FORGEML_POSTGRES_USER:-forgeml}"
POSTGRES_DB="${FORGEML_POSTGRES_DB:-forgeml}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TARGET="${BACKUP_DIR}/forgeml-${POSTGRES_DB}-${TIMESTAMP}.sql"

mkdir -p "${BACKUP_DIR}"

docker compose -f "${COMPOSE_FILE}" --profile core exec -T postgres \
  pg_dump --no-owner --no-privileges -U "${POSTGRES_USER}" "${POSTGRES_DB}" > "${TARGET}"

gzip -f "${TARGET}"
printf 'Created backup %s.gz\n' "${TARGET}"
