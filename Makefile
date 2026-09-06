.PHONY: check lint test web-check contrast placeholders api web

UV := uv run

check: lint test contrast placeholders web-check

lint:
	$(UV) ruff check services tests scripts
	$(UV) ruff format --check services tests scripts

test:
	$(UV) pytest -q

contrast:
	cd apps/web && node scripts/check-contrast.mjs

placeholders:
	$(UV) python scripts/placeholder_scan.py

web-check:
	cd apps/web && npm run typecheck

api:
	$(UV) uvicorn services.api.main:app --reload --port 8000

web:
	cd apps/web && npm run dev
