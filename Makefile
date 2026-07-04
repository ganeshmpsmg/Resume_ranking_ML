# ── Resume Ranking System — Makefile ─────────────────────────────
.PHONY: help up down build logs shell-backend shell-frontend \
        migrate test lint format clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Docker ───────────────────────────────────────────────────────
up:  ## Start all services (Postgres, Redis, Backend, Frontend)
	docker compose up -d

build:  ## Rebuild and start all services
	docker compose up --build -d

down:  ## Stop all services
	docker compose down

down-v:  ## Stop all services and wipe volumes (full reset)
	docker compose down -v

logs:  ## Tail all logs
	docker compose logs -f

logs-backend:  ## Tail backend logs
	docker compose logs -f backend

shell-backend:  ## Open a shell in the backend container
	docker compose exec backend bash

shell-frontend:  ## Open a shell in the frontend container
	docker compose exec frontend bash

# ── Database ─────────────────────────────────────────────────────
migrate:  ## Run Alembic migrations
	docker compose exec backend alembic upgrade head

migrate-local:  ## Run Alembic migrations locally
	cd backend && alembic upgrade head

# ── Local dev (no Docker) ─────────────────────────────────────────
install-backend:  ## Install backend deps locally
	cd backend && pip install -r requirements.dev.txt && \
	python -m spacy download en_core_web_sm

install-frontend:  ## Install frontend deps locally
	cd frontend && pip install -r requirements.txt

run-backend:  ## Run FastAPI backend locally with hot-reload
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

run-frontend:  ## Run Streamlit frontend locally
	cd frontend && streamlit run app.py

# ── Tests & Quality ───────────────────────────────────────────────
test:  ## Run backend unit tests
	cd backend && pytest tests/ -v

test-cov:  ## Run tests with coverage report
	cd backend && pytest tests/ -v --cov=app --cov-report=term-missing

lint:  ## Lint backend code (flake8 + mypy)
	cd backend && flake8 app/ tests/ && mypy app/

format:  ## Auto-format code (black + isort)
	cd backend && black app/ tests/ && isort app/ tests/

clean:  ## Remove Python cache files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -name "*.pyc" -delete 2>/dev/null; true
	find . -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null; true
