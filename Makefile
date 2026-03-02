UVICORN_APP := app.main:app
UVICORN_HOST := 0.0.0.0
UVICORN_PORT := 8000
UV_PROJECT_ENV := $(shell if [ -d .venv-wsl ]; then echo .venv-wsl; else echo .venv; fi)

.PHONY: start stop up down frontend

start:
	UV_PROJECT_ENVIRONMENT="$(UV_PROJECT_ENV)" uv run --no-sync uvicorn "$(UVICORN_APP)" --host "$(UVICORN_HOST)" --port "$(UVICORN_PORT)"

stop:
	@PIDS="$$(pgrep -f 'uvicorn $(UVICORN_APP) --host $(UVICORN_HOST) --port $(UVICORN_PORT)' || true)"; \
	if [ -z "$$PIDS" ]; then \
		echo "uvicorn is not running."; \
	else \
		echo "$$PIDS" | xargs kill; \
		echo "uvicorn stopped (pid=$$PIDS)."; \
	fi

up:
	docker compose up --build -d

down:
	docker compose down

frontend:
	cd frontend && npm run dev
