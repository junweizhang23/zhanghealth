.PHONY: help install install-dev lint format test

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install package
	pip install -e .

install-dev: ## Install with dev dependencies
	pip install -e ".[dev]"

lint: ## Run linter
	ruff check .

format: ## Auto-format code
	ruff format .
	ruff check --fix .

test: ## Run tests
	pytest

test-cov: ## Run tests with coverage
	pytest --cov=src --cov-report=term-missing
