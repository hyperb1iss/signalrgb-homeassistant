.PHONY: install test coverage lint typecheck format check fix build update clean

install:
	uv sync --locked

test:
	uv run --locked pytest

coverage:
	uv run --locked pytest --cov --cov-report=term-missing --cov-report=html

lint:
	uv run --locked ruff check custom_components tests scripts
	uv run --locked ruff format --check custom_components tests scripts

typecheck:
	uv run --locked ty check

format:
	uv run --locked ruff format custom_components tests scripts

check: lint typecheck test

fix:
	uv run --locked ruff check --fix custom_components tests scripts
	uv run --locked ruff format custom_components tests scripts

build:
	uv build

update:
	@test -n "$(HASS_CONFIG_DIR)" || (echo "Set HASS_CONFIG_DIR to your Home Assistant config directory"; exit 1)
	uv run --no-project scripts/release.py update-hass --config-dir "$(HASS_CONFIG_DIR)"

clean:
	rm -rf .coverage htmlcov dist build
