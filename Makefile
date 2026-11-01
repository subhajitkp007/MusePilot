# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0

.PHONY: help setup lint format test health demo-w1 demo-w2 replay-w1 replay-w2 server app-analyze app-test app-web docker-build docker-up docker-down clean

PYTHON := .venv/bin/python
PIP := .venv/bin/pip
RUFF := .venv/bin/ruff
PYTEST := .venv/bin/pytest
FLUTTER ?= flutter

help: ## Show this help menu
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Initialize virtual environment and install dependencies
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

lint: ## Run Ruff linter and security checks
	$(RUFF) check musepilot tests

format: ## Format code with Ruff
	$(RUFF) format musepilot tests
	$(RUFF) check --fix musepilot tests

test: ## Run unit and golden-trace fixture test suite
	$(PYTEST) tests/

health: ## Run pre-flight calibration & health check
	$(PYTHON) -m musepilot.health.checker

demo-w1: ## Execute Workflow 1 (Precision Canvas Grounding)
	$(PYTHON) -m musepilot.cli run --workflow w1

demo-w2: ## Execute Workflow 2 (Voice Cross-App + Self-Healing Modal Recovery)
	$(PYTHON) -m musepilot.cli run --workflow w2 --inject-modal

replay-w1: ## Replay golden trace for Workflow 1 deterministically
	$(PYTHON) -m musepilot.cli replay --workflow w1

replay-w2: ## Replay golden trace for Workflow 2 deterministically
	$(PYTHON) -m musepilot.cli replay --workflow w2

eval: ## Run quantitative evaluation benchmark over historical traces
	$(PYTHON) -m musepilot.cli eval

server: ## Launch the HUD API server for Flutter clients (http://localhost:8501)
	$(PYTHON) -m musepilot.server.app

app-analyze: ## Analyze the Flutter HUD app
	cd app && $(FLUTTER) analyze

app-test: ## Run the Flutter HUD test suite
	cd app && $(FLUTTER) test

app-web: ## Build the Flutter web HUD into the API server static dir
	cd app && $(FLUTTER) build web --release --output ../musepilot/server/static/web

docker-build: ## Build production Docker image
	docker compose build

docker-up: ## Start full MusePilot Docker stack (Agent + HUD + Canvas Server + Jaeger)
	docker compose up -d

docker-down: ## Stop all MusePilot Docker containers
	docker compose down

clean: ## Clean caches and temporary artifacts
	rm -rf .pytest_cache .ruff_cache __pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} +

