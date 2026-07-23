# Backup and Restore Runbook

ForgeML stores control-plane state in PostgreSQL. Backups must be created before migrations and before high-risk operational changes.

## Create a Backup

```bash
scripts/ops/backup_postgres.sh
```

By default the backup is written to `backups/postgres` and compressed with gzip. Override locations and database settings with:

- `FORGEML_COMPOSE_FILE`
- `FORGEML_BACKUP_DIR`
- `FORGEML_POSTGRES_USER`
- `FORGEML_POSTGRES_DB`

## Restore a Backup

```bash
scripts/ops/restore_postgres.sh backups/postgres/forgeml-forgeml-20260722T010000Z.sql.gz
```

Restore only into the intended environment. For production, require approval from the incident lead and database owner before running a restore.

## Validation

After restore:

1. Run `/health/ready`.
2. Confirm Alembic head matches the application release.
3. Query one project, dataset, model, deployment, and alert rule through the API.
4. Confirm Grafana receives API metrics again.
5. Attach the restore command output to the incident or release record.
