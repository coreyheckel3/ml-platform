# Database Contracts

Database contracts capture schema-evolution invariants that must remain stable
as modules add or change persisted state.

## Alembic Migrations

`alembic-migrations.v1.json` records the checked Alembic revision graph, base
revision, head revision, branch points, merge revisions, and migration files.

Regenerate after an intentional migration change:

```bash
PYTHONPATH=backend/src:. python scripts/ci/check_alembic_migration_contract.py --write
```

Verify the checked-in contract:

```bash
PYTHONPATH=backend/src:. python scripts/ci/check_alembic_migration_contract.py
```

## SQLAlchemy Schema

`sqlalchemy-schema.v1.json` records the checked application metadata contract,
including tables, columns, primary keys, foreign keys, indexes, and unique
constraints compiled for PostgreSQL.

Regenerate after an intentional ORM schema change:

```bash
PYTHONPATH=backend/src:. python scripts/ci/check_sqlalchemy_schema_contract.py --write
```

Verify the checked-in contract:

```bash
PYTHONPATH=backend/src:. python scripts/ci/check_sqlalchemy_schema_contract.py
```
