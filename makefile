# 格式化代码 + 修复导入
format:
	uv run ruff check --fix .
	uv run ruff format .

# 仅检查代码，不修改
lint:
	uv run ruff check .

# 类型检查
typecheck:
	uv run mypy backend

# 本地启动 FastAPI
serve:
	uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
