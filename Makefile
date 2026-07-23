PYTHON ?= .venv/bin/python
RUFF ?= .venv/bin/ruff
UVICORN ?= .venv/bin/uvicorn
NPM ?= npm

.PHONY: backend-dev frontend-dev test backend-test frontend-test lint format docker-up docker-down

backend-dev:
	$(UVICORN) forgeml.main:create_app --factory --host 0.0.0.0 --port 8000 --reload --app-dir backend/src

frontend-dev:
	$(NPM) --prefix frontend run dev

test: backend-test frontend-test

backend-test:
	$(PYTHON) -m pytest backend/tests

frontend-test:
	$(NPM) --prefix frontend run test -- --run

lint:
	$(RUFF) check backend/src backend/tests scripts/dev
	$(NPM) --prefix frontend run lint

format:
	$(RUFF) format backend/src backend/tests scripts/dev
	$(NPM) --prefix frontend run format

docker-up:
	docker compose -f infra/compose/docker-compose.yml --profile core up --build

docker-down:
	docker compose -f infra/compose/docker-compose.yml --profile core down
