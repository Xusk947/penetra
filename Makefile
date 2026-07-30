.PHONY: backend frontend stop

backend:
	cd backend && .venv/bin/langgraph dev --no-browser --port 2024 --no-reload

frontend:
	cd frontend && pnpm dev

stop:
	-pkill -f "langgraph dev --no-browser --port 2024 --no-reload"
