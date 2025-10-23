# Makefile for ComputerUseAI

.PHONY: help install dev-install test clean build run setup-models

# Default target
help:
	@echo "ComputerUseAI - Desktop AI Assistant"
	@echo ""
	@echo "Available targets:"
	@echo "  install        Install the package"
	@echo "  dev-install    Install in development mode with dev dependencies"
	@echo "  test           Run tests"
	@echo "  clean          Clean build artifacts"
	@echo "  build          Build executable"
	@echo "  run            Run the application"
	@echo "  setup-models   Download required models"
	@echo "  lint           Run linting checks"
	@echo "  format         Format code with black"

# Installation
install:
	pip install -e .

dev-install:
	pip install -e ".[dev,build]"

# Testing
test:
	python -m pytest tests/ -v --cov=src --cov-report=html --cov-report=term

test-fast:
	python -m pytest tests/ -v -x

# Code quality
lint:
	flake8 src/ tests/
	mypy src/

format:
	black src/ tests/ build.py setup.py

# Setup
setup-models:
	python tools/model_setup.py

# Development
run:
	python -m src.main

run-dev:
	python run.py

# Building
build:
	python build.py --platform current

build-all:
	python build.py --platform all

build-windows:
	python build.py --platform windows

build-macos:
	python build.py --platform macos

build-linux:
	python build.py --platform linux

# Cleaning
clean:
	python build.py --clean
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Documentation
docs:
	@echo "Generating documentation..."
	@echo "See docs/ directory for generated documentation"

# Release
release-check:
	@echo "Checking release requirements..."
	python -c "import sys; assert sys.version_info >= (3, 8), 'Python 3.8+ required'"
	python -m pytest tests/ -v
	python -m flake8 src/ tests/
	@echo "✓ Release checks passed"

# Docker (for cross-platform builds)
docker-build:
	docker build -t computeruseai-builder .

docker-build-all:
	docker run --rm -v $(PWD):/workspace computeruseai-builder python build.py --platform all

# CI/CD helpers
ci-install:
	pip install -r requirements.txt
	pip install pytest pytest-cov flake8 mypy black

ci-test:
	python -m pytest tests/ -v --cov=src --cov-report=xml

ci-lint:
	flake8 src/ tests/
	mypy src/

# Development helpers
dev-setup: dev-install setup-models
	@echo "Development environment setup complete"
	@echo "Run 'make run' to start the application"

# Quick start
quickstart: install setup-models
	@echo "Quick start setup complete"
	@echo "Run 'make run' to start the application"
