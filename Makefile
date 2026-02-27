.PHONY: help build up down restart logs shell shell-db test test-cov clean install install-dev migrate migrate-create migrate-down migrate-history format format-check lint type-check security safety-check lint-all check check-all run dev db-reset db-backup db-restore prune worker-logs worker-restart redis-cli redis-monitor redis-stats pre-commit-install pre-commit-run pre-commit-update webapp-install webapp-lint webapp-lint-fix webapp-format webapp-format-check webapp-check quality-report

# Default target
.DEFAULT_GOAL := help

# Variables
DOCKER_COMPOSE = docker-compose
PYTHON = python
PIP = pip
APP_CONTAINER = mattilda_api
DB_CONTAINER = mattilda_db

# Colors for output
BLUE = \033[0;34m
GREEN = \033[0;32m
YELLOW = \033[0;33m
RED = \033[0;31m
NC = \033[0m # No Color

##@ Help

help: ## Display this help message
	@echo "$(BLUE)Mattilda School Management API - Makefile Commands$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n  make $(GREEN)<target>$(NC)\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(BLUE)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Docker Operations

build: ## Build Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	$(DOCKER_COMPOSE) build

up: ## Start all services (detached)
	@echo "$(BLUE)Starting services...$(NC)"
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)Services started!$(NC)"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"
	@echo "Front: http://localhost:3000"
	@echo "Monitoring: http://localhost:3001"

down: ## Stop all services
	@echo "$(YELLOW)Stopping services...$(NC)"
	$(DOCKER_COMPOSE) down
	@echo "$(GREEN)Services stopped!$(NC)"

restart: down up ## Restart all services

logs: ## View logs from all services
	$(DOCKER_COMPOSE) logs -f

logs-app: ## View logs from app service only
	$(DOCKER_COMPOSE) logs -f web

logs-db: ## View logs from database service only
	$(DOCKER_COMPOSE) logs -f db

logs-redis: ## View logs from Redis service only
	$(DOCKER_COMPOSE) logs -f redis

logs-worker: ## View logs from worker service only
	$(DOCKER_COMPOSE) logs -f worker

##@ Container Access

shell: ## Access bash shell in app container
	@echo "$(BLUE)Accessing app container shell...$(NC)"
	$(DOCKER_COMPOSE) exec web bash

shell-db: ## Access PostgreSQL shell in database container
	@echo "$(BLUE)Accessing database shell...$(NC)"
	$(DOCKER_COMPOSE) exec db psql -U mattilda -d mattilda_db

shell-python: ## Access Python REPL in app container
	@echo "$(BLUE)Accessing Python REPL...$(NC)"
	$(DOCKER_COMPOSE) exec web python

db-shell: ## Access interactive database shell with async support
	@echo "$(BLUE)Accessing database shell...$(NC)"
	$(DOCKER_COMPOSE) exec web python scripts/db_shell.py

db-shell-local: ## Access interactive database shell locally
	@echo "$(BLUE)Accessing local database shell...$(NC)"
	python scripts/db_shell.py

##@ Development (Local)

install: ## Install Python dependencies locally
	@echo "$(BLUE)Installing dependencies...$(NC)"
	$(PIP) install -r requirements.txt
	@echo "$(GREEN)Dependencies installed!$(NC)"

run: ## Run app locally (without Docker)
	@echo "$(BLUE)Starting local development server...$(NC)"
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev: ## Run app locally with debug mode
	@echo "$(BLUE)Starting development server with debug mode...$(NC)"
	DEBUG=True uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug

##@ Database Operations

migrate: ## Run database migrations (upgrade to latest)
	@echo "$(BLUE)Running database migrations...$(NC)"
	$(DOCKER_COMPOSE) exec web alembic upgrade head
	@echo "$(GREEN)Migrations completed!$(NC)"

migrate-local: ## Run migrations locally (without Docker)
	@echo "$(BLUE)Running local database migrations...$(NC)"
	alembic upgrade head
	@echo "$(GREEN)Migrations completed!$(NC)"

migrate-create: ## Create a new migration (usage: make migrate-create msg="description")
	@echo "$(BLUE)Creating new migration...$(NC)"
	$(DOCKER_COMPOSE) exec web alembic revision --autogenerate -m "$(msg)"
	@echo "$(GREEN)Migration created!$(NC)"

migrate-create-local: ## Create migration locally (usage: make migrate-create-local msg="description")
	@echo "$(BLUE)Creating new migration locally...$(NC)"
	alembic revision --autogenerate -m "$(msg)"
	@echo "$(GREEN)Migration created!$(NC)"

migrate-down: ## Rollback last migration
	@echo "$(YELLOW)Rolling back last migration...$(NC)"
	$(DOCKER_COMPOSE) exec web alembic downgrade -1
	@echo "$(GREEN)Rollback completed!$(NC)"

migrate-history: ## Show migration history
	$(DOCKER_COMPOSE) exec web alembic history

db-reset: down ## Reset database (WARNING: deletes all data)
	@echo "$(RED)WARNING: This will delete all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(YELLOW)Removing database volume...$(NC)"; \
		docker volume rm mattilda_postgres_data 2>/dev/null || true; \
		echo "$(GREEN)Database reset complete!$(NC)"; \
		echo "Run 'make up' and 'make migrate' to start fresh"; \
	fi

db-backup: ## Backup database to file (usage: make db-backup file=backup.sql)
	@echo "$(BLUE)Backing up database...$(NC)"
	@mkdir -p backups
	$(DOCKER_COMPOSE) exec -T db pg_dump -U mattilda -d mattilda_db > backups/$$(date +%Y%m%d_%H%M%S)_backup.sql
	@echo "$(GREEN)Backup completed!$(NC)"

db-restore: ## Restore database from file (usage: make db-restore file=backups/backup.sql)
	@echo "$(YELLOW)Restoring database from $(file)...$(NC)"
	$(DOCKER_COMPOSE) exec -T db psql -U mattilda -d mattilda_db < $(file)
	@echo "$(GREEN)Restore completed!$(NC)"

##@ Event-Driven Accounting

redis-cli: ## Access Redis CLI
	@echo "$(BLUE)Accessing Redis CLI...$(NC)"
	$(DOCKER_COMPOSE) exec redis redis-cli

redis-monitor: ## Monitor Redis commands in real-time
	@echo "$(BLUE)Monitoring Redis commands...$(NC)"
	$(DOCKER_COMPOSE) exec redis redis-cli MONITOR

redis-stats: ## Show Redis statistics
	@echo "$(BLUE)Redis Statistics:$(NC)"
	@$(DOCKER_COMPOSE) exec redis redis-cli INFO stats | grep -E "total_commands_processed|instantaneous_ops_per_sec|keyspace"

redis-queue: ## Show current job queue length
	@echo "$(BLUE)Current queue length:$(NC)"
	@$(DOCKER_COMPOSE) exec redis redis-cli LLEN arq:queue:default || echo "0"

worker-restart: ## Restart the background worker
	@echo "$(YELLOW)Restarting worker...$(NC)"
	$(DOCKER_COMPOSE) restart worker
	@echo "$(GREEN)Worker restarted!$(NC)"

worker-logs: logs-worker ## Alias for logs-worker

worker-status: ## Check worker container status
	@echo "$(BLUE)Worker Status:$(NC)"
	@$(DOCKER_COMPOSE) ps worker

movements-recent: ## Show recent account movements (last 10)
	@echo "$(BLUE)Recent Account Movements:$(NC)"
	@$(DOCKER_COMPOSE) exec db psql -U mattilda -d mattilda_db -c \
		"SELECT id, movement_type, entity_type, delta, description, created_at FROM account_movements ORDER BY created_at DESC LIMIT 10;"

movements-summary: ## Show movement summary by type
	@echo "$(BLUE)Movement Summary:$(NC)"
	@$(DOCKER_COMPOSE) exec db psql -U mattilda -d mattilda_db -c \
		"SELECT movement_type, COUNT(*) as count, SUM(delta) as total_delta FROM account_movements GROUP BY movement_type;"

snapshots-list: ## List recent snapshots
	@echo "$(BLUE)Recent Snapshots:$(NC)"
	@$(DOCKER_COMPOSE) exec db psql -U mattilda -d mattilda_db -c \
		"SELECT entity_type, entity_id, snapshot_date, snapshot_type, total_invoiced, total_paid, total_pending FROM account_snapshots ORDER BY snapshot_date DESC LIMIT 10;"

##@ Testing

test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	pytest

test-docker: ## Run tests in Docker container
	@echo "$(BLUE)Running tests in Docker...$(NC)"
	$(DOCKER_COMPOSE) exec web pytest

test-cov: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	pytest --cov=app --cov-report=html --cov-report=term-missing
	@echo "$(GREEN)Coverage report generated in htmlcov/index.html$(NC)"

test-watch: ## Run tests in watch mode (requires pytest-watch)
	@echo "$(BLUE)Running tests in watch mode...$(NC)"
	ptw -- -v

##@ Code Quality (Backend)

install-dev: ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	$(PIP) install -r requirements-dev.txt
	@echo "$(GREEN)Development dependencies installed!$(NC)"

format: ## Format Python code with black and isort
	@echo "$(BLUE)Formatting Python code...$(NC)"
	black app tests scripts
	isort app tests scripts
	@echo "$(GREEN)Python code formatted!$(NC)"

format-check: ## Check Python code formatting without making changes
	@echo "$(BLUE)Checking Python code formatting...$(NC)"
	black --check app tests scripts
	isort --check-only app tests scripts

lint: ## Lint Python code with flake8
	@echo "$(BLUE)Linting Python code with flake8...$(NC)"
	flake8 app tests scripts
	@echo "$(GREEN)Flake8 linting completed!$(NC)"

type-check: ## Type check Python code with mypy
	@echo "$(BLUE)Type checking Python code...$(NC)"
	mypy app
	@echo "$(GREEN)Type checking completed!$(NC)"

security: ## Run security checks with bandit
	@echo "$(BLUE)Running security checks...$(NC)"
	bandit -r app -c pyproject.toml
	@echo "$(GREEN)Security checks completed!$(NC)"

safety-check: ## Check dependencies for known vulnerabilities
	@echo "$(BLUE)Checking dependencies for vulnerabilities...$(NC)"
	safety check --json
	@echo "$(GREEN)Safety check completed!$(NC)"

lint-all: lint type-check security ## Run all Python linting checks

##@ Code Quality (Frontend)

webapp-install: ## Install frontend dependencies
	@echo "$(BLUE)Installing frontend dependencies...$(NC)"
	cd webapp && npm install
	@echo "$(GREEN)Frontend dependencies installed!$(NC)"

webapp-lint: ## Lint frontend code with ESLint
	@echo "$(BLUE)Linting frontend code...$(NC)"
	cd webapp && npm run lint
	@echo "$(GREEN)Frontend linting completed!$(NC)"

webapp-lint-fix: ## Fix frontend linting issues automatically
	@echo "$(BLUE)Fixing frontend linting issues...$(NC)"
	cd webapp && npm run lint:fix
	@echo "$(GREEN)Frontend linting fixed!$(NC)"

webapp-format: ## Format frontend code with Prettier
	@echo "$(BLUE)Formatting frontend code...$(NC)"
	cd webapp && npm run format
	@echo "$(GREEN)Frontend code formatted!$(NC)"

webapp-format-check: ## Check frontend code formatting
	@echo "$(BLUE)Checking frontend code formatting...$(NC)"
	cd webapp && npm run format:check

webapp-check: webapp-lint webapp-format-check ## Run all frontend checks

##@ Code Quality (All)

pre-commit-install: ## Install pre-commit git hooks
	@echo "$(BLUE)Installing pre-commit hooks...$(NC)"
	pre-commit install
	@echo "$(GREEN)Pre-commit hooks installed!$(NC)"
	@echo "Hooks will run automatically on git commit"

pre-commit-run: ## Run pre-commit on all files
	@echo "$(BLUE)Running pre-commit on all files...$(NC)"
	pre-commit run --all-files

pre-commit-update: ## Update pre-commit hooks to latest versions
	@echo "$(BLUE)Updating pre-commit hooks...$(NC)"
	pre-commit autoupdate
	@echo "$(GREEN)Pre-commit hooks updated!$(NC)"

check: format-check lint-all test ## Run all backend checks (format, lint, type-check, security, test)

check-all: check webapp-check ## Run all checks for backend and frontend

quality-report: ## Generate comprehensive quality report
	@echo "$(BLUE)Generating quality report...$(NC)"
	@echo "Running tests with coverage..."
	@pytest --cov=app --cov-report=html --cov-report=term-missing
	@echo ""
	@echo "Running linters..."
	@flake8 app tests scripts || true
	@echo ""
	@echo "Running type checker..."
	@mypy app || true
	@echo ""
	@echo "Running security checks..."
	@bandit -r app -c pyproject.toml || true
	@echo ""
	@echo "$(GREEN)Quality report completed!$(NC)"
	@echo "Coverage report: htmlcov/index.html"

##@ Cleanup

clean: ## Remove Python cache files
	@echo "$(BLUE)Cleaning Python cache files...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.py~" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)Cleanup completed!$(NC)"

prune: down clean ## Remove all containers, images, volumes (DANGEROUS!)
	@echo "$(RED)WARNING: This will remove all Docker containers, images, and volumes!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(YELLOW)Removing containers and volumes...$(NC)"; \
		docker-compose down -v --remove-orphans; \
		docker system prune -af --volumes; \
		echo "$(GREEN)Prune completed!$(NC)"; \
	fi

##@ Utilities

env: ## Copy .env.example to .env if not exists
	@if [ ! -f .env ]; then \
		echo "$(BLUE)Creating .env file from .env.example...$(NC)"; \
		cp .env.example .env; \
		echo "$(GREEN).env file created!$(NC)"; \
		echo "$(YELLOW)Please update .env with your configuration$(NC)"; \
	else \
		echo "$(YELLOW).env file already exists$(NC)"; \
	fi

seed: ## Seed database with sample data
	@echo "$(BLUE)Seeding database...$(NC)"
	$(DOCKER_COMPOSE) exec web python scripts/seed_data.py
	@echo "$(GREEN)Database seeded!$(NC)"

seed-local: ## Seed database locally (without Docker)
	@echo "$(BLUE)Seeding local database...$(NC)"
	python scripts/seed_data.py
	@echo "$(GREEN)Database seeded!$(NC)"

ps: ## Show running containers
	$(DOCKER_COMPOSE) ps

stats: ## Show container resource usage
	docker stats $(APP_CONTAINER) $(DB_CONTAINER)

health: ## Check health of services
	@echo "$(BLUE)Checking service health...$(NC)"
	@curl -s http://localhost:8000/health | python -m json.tool || echo "$(RED)API is not responding$(NC)"

docs: ## Open API documentation in browser
	@echo "$(BLUE)Opening API documentation...$(NC)"
	@open http://localhost:8000/docs || xdg-open http://localhost:8000/docs || echo "Please visit http://localhost:8000/docs"

##@ Quick Start

setup: env build up migrate ## Initial setup (env, build, up, migrate)
	@echo "$(GREEN)Setup completed!$(NC)"
	@echo ""
	@echo "$(BLUE)Your application is ready!$(NC)"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"
	@echo ""
	@echo "Next steps:"
	@echo "  make logs      - View logs"
	@echo "  make shell     - Access container shell"
	@echo "  make test      - Run tests"

start: up ## Alias for 'up'

stop: down ## Alias for 'down'

rebuild: down build up migrate ## Rebuild and restart everything
	@echo "$(GREEN)Rebuild completed!$(NC)"
