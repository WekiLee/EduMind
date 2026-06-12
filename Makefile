.PHONY: install-backend install-frontend install dev-backend dev-frontend dev test lint validate-compose clean docker-up docker-up-prod docker-down docker-logs

# ── Install ──

install-backend:
	cd backend && pip install -r requirements.txt && pip install ruff mypy pytest pytest-cov

install-frontend:
	cd frontend && npm install

install: install-backend install-frontend

# ── Development ──

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev -- --host 0.0.0.0

dev:
	@echo "Run dev-backend and dev-frontend in separate terminals"

# ── Quality ──

lint:
	cd backend && ruff check . && mypy app --ignore-missing-imports

validate-compose:
	python scripts/validate_compose_config.py

format:
	cd backend && ruff format .

test:
	cd backend && python -m pytest tests/ -v --cov=app

test-unit:
	cd backend && python -m pytest tests/unit -v

# ── Docker ──

docker-up:
	@echo "请先设置 POSTGRES_PASSWORD，例如：export POSTGRES_PASSWORD=edumind_dev"
	docker compose --profile dev up -d

docker-up-prod:
	python scripts/validate_compose_config.py
	docker compose --profile prod build
	docker compose up -d postgres neo4j redis
	docker compose --profile prod run --rm backend-prod alembic upgrade head
	docker compose --profile prod up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

# ── Cleanup ──

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
	find . -name "*.pyc" -delete 2>/dev/null
	rm -rf .coverage coverage_report/
