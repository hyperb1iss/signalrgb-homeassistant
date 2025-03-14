.PHONY: install test lint format check clean

install:
	uv sync

test:
	uv run pytest

lint:
	uv run pylint custom_components tests
	uv run mypy custom_components tests
	uv run ruff check

format:
	uv run ruff format

check:
	uv run ruff format --check
	uv run pylint custom_components
	uv run mypy custom_components
	uv run ruff check

update:
	@./scripts/release.py update-hass

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*~" -delete
