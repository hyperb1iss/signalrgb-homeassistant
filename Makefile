.PHONY: install test coverage lint typecheck format check fix update clean

install:
	uv sync

test:
	uv run pytest

coverage:
	uv run pytest --cov --cov-report=term-missing --cov-report=html

lint:
	uv run ruff check custom_components tests
	uv run ruff format --check custom_components tests

typecheck:
	uv run ty check

format:
	uv run ruff format custom_components tests

check: lint typecheck test

fix:
	uv run ruff check --fix custom_components tests
	uv run ruff format custom_components tests

update:
	@./scripts/release.py update-hass

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*~" -delete
	rm -rf .coverage htmlcov dist build
