#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  printf 'Usage: %s path/to/forgeml-backup.sql.gz\n' "$0" >&2
  exit 2
fi

COMPOSE_FILE="${FORGEML_COMPOSE_FILE:-infra/compose/docker-compose.yml}"
POSTGRES_USER="${FORGEML_POSTGRES_USER:-forgeml}"
POSTGRES_DB="${FORGEML_POSTGRES_DB:-forgeml}"
BACKUP_FILE="$1"

if [[ ! -f "${BACKUP_FILE}" ]]; then
  printf 'Backup file does not exist: %s\n' "${BACKUP_FILE}" >&2
  exit 2
fi

gzip -dc "${BACKUP_FILE}" | docker compose -f "${COMPOSE_FILE}" --profile core exec -T postgres \
  psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"

printf 'Restored backup %s into database %s\n' "${BACKUP_FILE}" "${POSTGRES_DB}"
