SHELL := /bin/bash
PYTHON ?= python3.12
BIN := $(CURDIR)/.venv/bin
export DBT_PROFILES_DIR := $(CURDIR)
export DBT_SEND_ANONYMOUS_USAGE_STATS := false
export PYTHONPATH := $(CURDIR)

.PHONY: setup refresh test app parse smoke
setup:
	$(PYTHON) -c 'import sys; assert sys.version_info[:2] == (3, 12), "Python 3.12 required"'
	$(PYTHON) -m venv .venv
	$(BIN)/python -m pip install -r requirements.txt
	$(BIN)/python -m pip check
	$(BIN)/python scripts/smoke.py

refresh:
	$(BIN)/python scripts/ingest.py $(if $(ZIP),--zip "$(ZIP)",)
	$(BIN)/dbt build
	$(BIN)/python scripts/audit.py

parse:
	$(BIN)/dbt parse --no-partial-parse
	$(BIN)/python scripts/document_metrics.py

smoke:
	$(BIN)/python scripts/smoke.py

test:
	$(BIN)/dbt test
	$(BIN)/python -m pytest -q tests/python
	$(BIN)/python scripts/golden.py
	$(BIN)/python scripts/check_app.py

app:
	$(BIN)/streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
