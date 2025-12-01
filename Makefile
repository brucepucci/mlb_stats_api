.PHONY: install lint reformat test test-unit test-integration test-slow coverage clean

install:  ## Install dependencies
	uv sync --dev

lint:  ## Check for linter issues
	uv run isort --check --profile black src/ tests/
	uv run black --check -t py310 src/ tests/
	uv run autoflake -r -c --remove-all-unused-imports --ignore-init-module-imports src/ tests/

reformat:  ## Fix linter issues
	uv run isort --profile black src/ tests/
	uv run black -t py310 src/ tests/
	uv run autoflake -r -i --remove-all-unused-imports --ignore-init-module-imports src/ tests/

test:  ## Run all tests
	uv run pytest tests/ -v

test-unit:  ## Run unit tests only
	uv run pytest tests/unit/ -v

test-integration:  ## Run integration tests (excluding slow)
	uv run pytest tests/integration/ -v -m "not slow"

test-slow:  ## Run slow integration tests (live API)
	uv run pytest tests/integration/ -v -m "slow"

coverage:  ## Run tests with coverage
	uv run pytest tests/ --cov=mlb_stats --cov-report=html --cov-report=term-missing

clean:  ## Clean up build artifacts
	rm -rf build/ dist/ *.egg-info .pytest_cache .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
