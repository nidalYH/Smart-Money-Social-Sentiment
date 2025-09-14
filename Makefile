# Smart Money Trading System - Makefile

.PHONY: help install install-dev test lint format security clean run run-dev run-prod build push deploy

help: ## Show this help message
	@echo "Smart Money Trading System - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements-dev.txt
	pre-commit install

test: ## Run tests
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term

test-watch: ## Run tests in watch mode
	pytest-watch tests/

lint: ## Run linting
	flake8 app/ tests/
	black --check app/ tests/
	isort --check-only app/ tests/
	mypy app/

format: ## Format code
	black app/ tests/
	isort app/ tests/

security: ## Run security checks
	safety check
	bandit -r app/
	semgrep --config=auto app/

clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/
	rm -rf logs/*.log

run: ## Run the application
	python complete_trading_system.py

run-dev: ## Run in development mode
	DEBUG=true LOG_LEVEL=DEBUG python complete_trading_system.py

run-prod: ## Run in production mode
	DEBUG=false LOG_LEVEL=WARNING python complete_trading_system.py

build: ## Build Docker image
	docker build -t smartmoney:latest .

build-dev: ## Build development Docker image
	docker build -f Dockerfile.dev -t smartmoney:dev .

run-docker: ## Run with Docker
	docker-compose up -d

run-docker-dev: ## Run development environment with Docker
	docker-compose -f docker-compose.yml -f development.yml up -d

run-docker-test: ## Run tests with Docker
	docker-compose -f testing.yml up --build test-runner

stop-docker: ## Stop Docker containers
	docker-compose down

logs: ## Show application logs
	docker-compose logs -f smartmoney

shell: ## Open shell in container
	docker-compose exec smartmoney /bin/bash

db-migrate: ## Run database migrations
	alembic upgrade head

db-rollback: ## Rollback database migrations
	alembic downgrade -1

db-reset: ## Reset database
	rm -f smartmoney.db
	python -c "from app.database import create_tables; create_tables()"

backup: ## Create database backup
	cp smartmoney.db backups/smartmoney_$(shell date +%Y%m%d_%H%M%S).db

restore: ## Restore database from backup
	@echo "Available backups:"
	@ls -la backups/
	@echo "Enter backup filename:"
	@read backup_file; cp backups/$$backup_file smartmoney.db

monitor: ## Start monitoring stack
	docker-compose -f monitoring.yml up -d

monitor-stop: ## Stop monitoring stack
	docker-compose -f monitoring.yml down

security-scan: ## Run comprehensive security scan
	safety check
	bandit -r app/
	semgrep --config=auto app/
	docker run --rm -v $(PWD):/app securecodewarrior/docker-security-scan:latest

performance-test: ## Run performance tests
	locust -f tests/performance/locustfile.py --host=http://localhost:8000

load-test: ## Run load tests
	pytest tests/performance/ -v

docs: ## Generate documentation
	sphinx-build -b html docs/ docs/_build/html

docs-serve: ## Serve documentation locally
	cd docs/_build/html && python -m http.server 8001

deploy-staging: ## Deploy to staging
	@echo "Deploying to staging..."
	# Add your staging deployment commands here

deploy-prod: ## Deploy to production
	@echo "Deploying to production..."
	# Add your production deployment commands here

setup: install-dev ## Initial setup
	@echo "Setting up development environment..."
	pre-commit install
	@echo "Development environment ready!"

ci: test lint security ## Run CI pipeline locally
	@echo "CI pipeline completed successfully!"

all: clean install-dev test lint security ## Run everything
	@echo "All checks passed!"
