PYTHON ?= .venv/bin/python
RUFF ?= .venv/bin/ruff
UVICORN ?= .venv/bin/uvicorn
NPM ?= npm

.PHONY: backend-dev frontend-dev test backend-test frontend-test example-training lint format production-readiness docker-up docker-down docker-full

backend-dev:
	$(UVICORN) forgeml.main:create_app --factory --host 0.0.0.0 --port 8000 --reload --app-dir backend/src

frontend-dev:
	$(NPM) --prefix frontend run dev

test: backend-test frontend-test

backend-test:
	$(PYTHON) -m pytest backend/tests

frontend-test:
	$(NPM) --prefix frontend run test -- --run

example-training:
	PYTHONPATH=. $(PYTHON) scripts/examples/run_local_training.py

lint:
	$(RUFF) check backend/src backend/tests scripts/ci scripts/dev scripts/examples scripts/workers ml/libraries ml/examples
	$(NPM) --prefix frontend run lint

format:
	$(RUFF) format backend/src backend/tests scripts/ci scripts/dev scripts/examples scripts/workers ml/libraries ml/examples
	$(NPM) --prefix frontend run format

production-readiness:
	$(PYTHON) scripts/ci/production_readiness.py
	docker compose -f infra/compose/docker-compose.yml --profile full config

docker-up:
	docker compose -f infra/compose/docker-compose.yml --profile core up --build

docker-full:
	docker compose -f infra/compose/docker-compose.yml --profile full up --build

docker-down:
	docker compose -f infra/compose/docker-compose.yml --profile core down
