.PHONY: dev prod test test-coverage lint logs down clean help

COMPOSE_PROD := docker compose -f docker-compose.yml
COMPOSE_DEV  := docker compose -f docker-compose.yml -f docker-compose.dev.yml

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

dev: ## Start full stack with hot reload (development)
	$(COMPOSE_DEV) up --build

prod: ## Start production build (detached)
	$(COMPOSE_PROD) up --build -d

test: ## Run backend tests inside container
	$(COMPOSE_DEV) run --rm --no-deps backend \
		sh -c "pip install --quiet -r requirements-dev.txt && pytest tests/ -v"

test-coverage: ## Run tests with coverage report
	$(COMPOSE_DEV) run --rm --no-deps backend \
		sh -c "pip install --quiet -r requirements-dev.txt && pytest tests/ -v \
			--cov=app --cov-report=term-missing --cov-report=html:htmlcov"

lint: ## Run ruff linter and format checker
	$(COMPOSE_DEV) run --rm --no-deps backend \
		sh -c "pip install --quiet -r requirements-dev.txt && \
			ruff check app/ tests/ && ruff format --check app/ tests/"

logs: ## Follow container logs
	$(COMPOSE_DEV) logs -f

down: ## Stop all services
	$(COMPOSE_DEV) down 2>/dev/null; \
	$(COMPOSE_PROD) down 2>/dev/null; \
	true

clean: ## Stop services, remove volumes and local images
	$(COMPOSE_DEV) down -v --rmi local --remove-orphans 2>/dev/null; \
	$(COMPOSE_PROD) down -v --rmi local --remove-orphans 2>/dev/null; \
	rm -rf htmlcov .coverage; \
	true
