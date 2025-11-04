.PHONY: help install test lint format clean docker-build docker-up docker-down docker-logs run-api run-cli

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies with UV
	uv sync

test: ## Run all tests with coverage
	uv run pytest --cov=specflow --cov-report=term-missing --cov-report=html

test-fast: ## Run tests without coverage
	uv run pytest -x

test-e2e: ## Run only E2E tests
	uv run pytest tests/test_e2e/ -v

lint: ## Run linter (ruff)
	uv run ruff check src/ tests/

format: ## Format code with ruff
	uv run ruff format src/ tests/

clean: ## Clean build artifacts and cache
	rm -rf build/ dist/ *.egg-info .pytest_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docker-build: ## Build Docker image
	docker build -t specflow:latest .

docker-up: ## Start services with docker-compose
	docker-compose up -d

docker-up-dev: ## Start services in development mode
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

docker-down: ## Stop all services
	docker-compose down

docker-logs: ## Show docker logs
	docker-compose logs -f

docker-shell: ## Open shell in running container
	docker exec -it specflow-api /bin/bash

docker-test: ## Run tests in Docker container
	docker-compose run --rm specflow-api pytest

run-api: ## Run API server locally
	uv run uvicorn specflow.api.main:app --reload

run-cli: ## Show CLI help
	uv run specflow --help

validate: ## Run full validation (lint + test)
	@echo "Running linter..."
	@make lint
	@echo "\nRunning tests..."
	@make test
	@echo "\n✅ Validation complete!"

deploy-local: ## Deploy locally with docker-compose
	@echo "Building image..."
	@make docker-build
	@echo "\nStarting services..."
	@make docker-up
	@echo "\n✅ SpecFlow running at http://localhost:8000"
	@echo "📖 API docs: http://localhost:8000/docs"

deploy-dev: ## Deploy in development mode
	@make docker-up-dev
	@echo "\n✅ SpecFlow dev mode running at http://localhost:8000"
