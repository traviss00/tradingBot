"""Makefile for common tasks."""

.PHONY: help setup dev test lint format clean docker docker-up docker-down

help:
	@echo "Trading System - Available Commands"
	@echo "===================================="
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup          - Setup environment and install dependencies"
	@echo "  make install        - Install dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make dev            - Start development servers"
	@echo "  make api            - Start API server only"
	@echo "  make dashboard      - Start Streamlit dashboard"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test           - Run tests"
	@echo "  make lint           - Run linting"
	@echo "  make format         - Format code"
	@echo "  make check          - Run all checks"
	@echo ""
	@echo "Docker:"
	@echo "  make docker         - Build Docker image"
	@echo "  make docker-up      - Start Docker services"
	@echo "  make docker-down    - Stop Docker services"
	@echo ""
	@echo "Utilities:"
	@echo "  make train          - Train model"
	@echo "  make backtest       - Run backtest"
	@echo "  make example        - Run example"
	@echo "  make clean          - Clean generated files"

setup:
	python setup_check.py
	pip install -r requirements.txt
	@echo "✅ Setup complete!"

install:
	pip install -r requirements.txt

dev:
	@echo "Starting development servers..."
	@echo "API: http://localhost:8000"
	@echo "Dashboard: http://localhost:8501"
	@echo "Docs: http://localhost:8000/docs"
	@echo ""
	@echo "Press Ctrl+C to stop"
	@echo ""
	python -m uvicorn app.main:app --reload &
	sleep 2
	streamlit run app/ui/dashboard.py

api:
	python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dashboard:
	streamlit run app/ui/dashboard.py

test:
	pytest tests/ -v --tb=short

lint:
	python scripts/utils.py lint

format:
	python scripts/utils.py format

check: test lint
	@echo "✅ All checks passed!"

docker:
	docker build -t trading-system:latest .

docker-up:
	docker-compose up -d
	@echo "✅ Services started"
	@echo "API: http://localhost:8000"
	@echo "Dashboard: http://localhost:8501"

docker-down:
	docker-compose down

train:
	python example.py

backtest:
	python example.py

example:
	python example.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov dist build *.egg-info
	@echo "✅ Cleaned up"
