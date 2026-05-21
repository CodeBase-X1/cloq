.PHONY: help install dev test lint format type-check docs clean

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install cloq in production mode
	pip install .

dev: ## Install cloq in development mode with all extras
	pip install -e ".[all]"
	pre-commit install

test: ## Run test suite with coverage
	pytest tests/ -v --cov=cloq --cov-report=term-missing

test-fast: ## Run tests without coverage (faster)
	pytest tests/ -v --no-cov

lint: ## Run linter (Ruff)
	ruff check src/ tests/
	ruff format --check src/ tests/

format: ## Auto-format code
	ruff check --fix src/ tests/
	ruff format src/ tests/

type-check: ## Run type checker (mypy)
	mypy src/cloq/

docs: ## Build documentation locally
	mkdocs serve

docs-build: ## Build documentation for deployment
	mkdocs build

clean: ## Clean build artifacts
	rm -rf dist/ build/ *.egg-info htmlcov/ .coverage .mypy_cache/ .pytest_cache/ site/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

check: lint type-check test ## Run all checks (lint + type-check + test)
