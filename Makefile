.PHONY: setup run test lint

setup:
	uv sync --all-extras

run:
	uv run python -m release_manager

test:
	uv run --extra dev pytest tests/ -v

lint:
	uv run ruff check src/ tests/
