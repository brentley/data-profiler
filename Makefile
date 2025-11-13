# VQ8 Data Profiler - Makefile
# Provides convenient commands for development, testing, and deployment

.PHONY: help install dev dev-build dev-down dev-logs test test-unit test-integration lint fmt clean build up down logs shell-api shell-web

# Default target
.DEFAULT_GOAL := help

# Build metadata
GIT_COMMIT := $(shell git rev-parse --short HEAD 2>/dev/null || echo "dev")
BUILD_DATE := $(shell date -u +"%Y-%m-%dT%H:%M:%SZ")
VERSION := 1.0.0

# Export for docker-compose
export GIT_COMMIT
export BUILD_DATE
export VERSION

##@ General

help: ## Display this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

install: ## Install development dependencies (Python + Node)
	@echo "Installing Python dependencies..."
	cd api && python -m pip install -r requirements.txt -r requirements-dev.txt
	@echo "Installing Node dependencies..."
	cd web && npm install
	@echo "Installing pre-commit hooks..."
	pre-commit install
	@echo "Installation complete!"

##@ Development

dev: ## Start development environment with hot reload
	@echo "Starting development environment..."
	@echo "GIT_COMMIT: $(GIT_COMMIT)"
	@echo "BUILD_DATE: $(BUILD_DATE)"
	@echo "VERSION: $(VERSION)"
	docker compose -f docker-compose.dev.yml up

dev-build: ## Build and start development environment
	@echo "Building development environment..."
	docker compose -f docker-compose.dev.yml build --build-arg GIT_COMMIT=$(GIT_COMMIT) --build-arg BUILD_DATE=$(BUILD_DATE) --build-arg VERSION=$(VERSION)
	docker compose -f docker-compose.dev.yml up

dev-down: ## Stop development environment
	docker compose -f docker-compose.dev.yml down

dev-logs: ## Follow development logs
	docker compose -f docker-compose.dev.yml logs -f

##@ Testing

test: ## Run all tests (unit + integration)
	@echo "Running all tests..."
	cd api && pytest tests/ -v --cov=. --cov-report=html --cov-report=term

test-unit: ## Run unit tests only
	@echo "Running unit tests..."
	cd api && pytest tests/unit/ -v --cov=. --cov-report=term

test-integration: ## Run integration tests only
	@echo "Running integration tests..."
	cd api && pytest tests/integration/ -v

test-watch: ## Run tests in watch mode
	@echo "Running tests in watch mode..."
	cd api && pytest-watch tests/ -v

##@ Code Quality

lint: ## Run linters (black, ruff, prettier)
	@echo "Linting Python code..."
	cd api && black --check . && ruff check .
	@echo "Linting TypeScript/JavaScript code..."
	cd web && npm run lint

fmt: ## Format code (black, ruff, prettier)
	@echo "Formatting Python code..."
	cd api && black . && ruff check --fix .
	@echo "Formatting TypeScript/JavaScript code..."
	cd web && npm run format

security: ## Run security scans (bandit, safety)
	@echo "Running security scans..."
	cd api && bandit -r . -ll && safety check

##@ Production

build: ## Build production images
	@echo "Building production images..."
	docker compose build --build-arg GIT_COMMIT=$(GIT_COMMIT) --build-arg BUILD_DATE=$(BUILD_DATE) --build-arg VERSION=$(VERSION)

up: ## Start production stack
	@echo "Starting production stack..."
	docker compose up -d

down: ## Stop production stack
	docker compose down

logs: ## Follow production logs
	docker compose logs -f

restart: ## Restart production stack
	docker compose restart

##@ Utilities

shell-api: ## Open shell in API container
	docker compose exec api /bin/bash

shell-web: ## Open shell in Web container
	docker compose exec web /bin/sh

clean: ## Clean temporary files and build artifacts
	@echo "Cleaning temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	rm -rf api/dist api/build
	rm -rf web/dist web/build web/node_modules/.cache
	@echo "Cleaning Docker resources..."
	docker compose down --volumes --remove-orphans
	@echo "Clean complete!"

clean-data: ## DANGER: Delete all data (work + outputs)
	@echo "WARNING: This will delete ALL data including outputs!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		rm -rf data/work/* data/outputs/*; \
		echo "\nData directories cleaned."; \
	else \
		echo "\nCancelled."; \
	fi

version: ## Display version information
	@echo "VQ8 Data Profiler"
	@echo "Version: $(VERSION)"
	@echo "Git Commit: $(GIT_COMMIT)"
	@echo "Build Date: $(BUILD_DATE)"

##@ Data Management

init-data: ## Initialize data directories
	@echo "Creating data directories..."
	mkdir -p data/work data/outputs
	@echo "Data directories created."

backup-outputs: ## Backup outputs to timestamped archive
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	echo "Creating backup: data_backup_$$TIMESTAMP.tar.gz"; \
	tar -czf data_backup_$$TIMESTAMP.tar.gz data/outputs/; \
	echo "Backup complete: data_backup_$$TIMESTAMP.tar.gz"
