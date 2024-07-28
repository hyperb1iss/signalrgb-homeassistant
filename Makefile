.PHONY: install test lint format check clean

install:
	poetry install

test:
	poetry run pytest

lint:
	poetry run pylint custom_components
	poetry run mypy custom_components
	poetry run ruff check .

format:
	poetry run black .
	poetry run isort .

check:
	poetry run black --check .
	poetry run isort --check .
	poetry run pylint custom_components
	poetry run mypy custom_components
	poetry run ruff check .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*~" -delete
