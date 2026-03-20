.PHONY: env uv pre-commit lint

env: uv pre-commit

uv:
	uv sync

pre-commit:
	uv run pre-commit install

lint:
	uv run pre-commit run --all-files
