.PHONY: help install format lint type-check test test-cov clean run-api run-worker

help:
	@echo "可用命令:"
	@echo "  make install      - 安装依赖"
	@echo "  make format       - 格式化代码"
	@echo "  make lint         - 代码检查"
	@echo "  make type-check   - 类型检查"
	@echo "  make test         - 运行测试"
	@echo "  make test-cov     - 运行测试并生成覆盖率报告"
	@echo "  make clean        - 清理临时文件"
	@echo "  make run-api      - 运行 API 服务器"
	@echo "  make run-worker   - 运行 Worker"

install:
	pip install -r requirements.txt

format:
	black src tests
	ruff check --fix src tests

lint:
	ruff check src tests

type-check:
	mypy src

test:
	pytest

test-cov:
	pytest --cov=src --cov-report=html --cov-report=term

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf htmlcov
	rm -rf .coverage

run-api:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

run-worker:
	python -m src.workers.task_worker
