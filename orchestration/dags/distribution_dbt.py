"""A manual, seven-step workflow around the existing distribution lab commands."""
from datetime import timedelta
import os
from pathlib import Path

import pendulum
from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator

# The launcher supplies this path, including when Airflow copies a DAG bundle.
ROOT = Path(os.environ['LAB_PROJECT_ROOT'])

with DAG(
    dag_id='distribution_dbt',
    description='SEC → dbt staging → marts → tests → MetricFlow → dashboard',
    start_date=pendulum.datetime(2025, 1, 1, tz='UTC'),
    schedule=None,  # Click Trigger; this fixed quarterly extract needs no daily schedule.
    catchup=False,
    max_active_runs=1,  # Do not let two runs write the same DuckDB file.
    max_active_tasks=1,
    dagrun_timeout=timedelta(minutes=30),
    default_args={
        'owner': 'distribution-lab',
        'retries': 1,
        'retry_delay': timedelta(seconds=15),
        'execution_timeout': timedelta(minutes=15),
    },
    tags=['learning', 'dbt', 'duckdb'],
    doc_md='''
### Start here
Trigger this DAG and open Graph. Click a task to inspect its command and logs.
All seven tasks must succeed. A failed task blocks its downstream tasks.

The run's logical date identifies an orchestration run; it does **not** choose
SEC report dates. Every run rebuilds the same cached 2025 Q4 extract.
Use the project virtualenv for dbt/MetricFlow and the separate Airflow virtualenv
for orchestration. Stop independent refresh/test commands while this DAG runs.
''',
) as dag:
    def command(task_id, shell_command):
        return BashOperator(
            task_id=task_id,
            bash_command=shell_command,
            cwd=str(ROOT),
            env={
                'DBT_PROFILES_DIR': str(ROOT),
                'DBT_SEND_ANONYMOUS_USAGE_STATS': 'false',
                'LAB_DB_PATH': str(ROOT / 'data/lab.duckdb'),
                'PYTHONPATH': str(ROOT),
                'PATH': str(ROOT / '.venv/bin') + os.pathsep + os.environ.get('PATH', ''),
            },
            append_env=True,
            do_xcom_push=False,  # Tables stay in DuckDB; Airflow stores task status/logs.
            skip_on_exit_code=None,  # Any nonzero exit is a failure, including 99.
        )

    ingest_sec = command('ingest_sec', '.venv/bin/python scripts/ingest.py')
    dbt_staging = command('dbt_staging', '.venv/bin/dbt build --select path:models/staging')
    dbt_marts = command('dbt_marts', '.venv/bin/dbt run --select path:models/marts')
    dbt_tests = command('dbt_tests', '.venv/bin/dbt test')
    golden_questions = command('golden_questions', '.venv/bin/python scripts/golden.py')
    audit = command('audit', '.venv/bin/python scripts/audit.py')
    dashboard_check = command('dashboard_check', '.venv/bin/python scripts/check_app.py')

    ingest_sec >> dbt_staging >> dbt_marts >> dbt_tests >> golden_questions >> audit >> dashboard_check
