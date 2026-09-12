SHELL := /bin/bash
PYTHON ?= python3.12
PORT ?= 8502
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
	$(BIN)/streamlit run app.py --server.address 127.0.0.1 --server.port $(PORT) --server.headless true --browser.gatherUsageStats false

# Optional local Airflow learning environment; separate from the dbt environment.
AIRFLOW_PORT ?= 8080
export AIRFLOW_PORT
AIRFLOW := $(BIN)/python orchestration/run.py
.PHONY: airflow-setup airflow airflow-check airflow-trigger airflow-status airflow-test
airflow-setup:
	$(PYTHON) -c 'import sys; assert sys.version_info[:2] == (3, 12), "Python 3.12 required"'
	$(PYTHON) -m venv .airflow-venv
	.airflow-venv/bin/python -m pip install -r orchestration/requirements.txt --constraint orchestration/constraints-3.12.txt
	.airflow-venv/bin/python -m pip check
	$(AIRFLOW) db migrate
	$(AIRFLOW) check

airflow:
	$(AIRFLOW) standalone

airflow-check:
	$(AIRFLOW) check

airflow-trigger:
	$(AIRFLOW) dags unpause distribution_dbt
	$(AIRFLOW) dags trigger distribution_dbt

airflow-status:
	$(AIRFLOW) dags list-runs distribution_dbt

airflow-test:
	$(AIRFLOW) dags test distribution_dbt
