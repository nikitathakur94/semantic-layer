# Learn Airflow with this lab

Airflow now orchestrates the existing pipeline. The SQL and metrics still live in
`models/`; no business formula moved into the DAG.

Start with `make airflow-setup`, then `make airflow`. Keep that terminal running.
Open [Airflow](http://localhost:8080), log in as **learner**, and use the locally
generated password from `.airflow/simple_auth_manager_passwords.json.generated`.
That file and the whole `.airflow/` directory are ignored by Git. The password
is created on the first server startup. To read it locally:

```bash
cat .airflow/simple_auth_manager_passwords.json.generated
```

Open **Dags → distribution_dbt**, turn it on if paused, then click **Trigger**.
Alternatively, use `make airflow-trigger` from another terminal. Open the new run's
**Graph** view and click any task to see its state, duration, rendered command and logs.

## What the seven tasks do

| Order / task | Existing command Airflow executes | What to look for in logs |
| --- | --- | --- |
| 1. `ingest_sec` | `.venv/bin/python scripts/ingest.py` | Cache reuse, source timestamps, 13,328 rows per raw table |
| 2. `dbt_staging` | `.venv/bin/dbt build --select path:models/staging` | Three views, source-key and relationship checks |
| 3. `dbt_marts` | `.venv/bin/dbt run --select path:models/marts` | Five tables built in dbt dependency order |
| 4. `dbt_tests` | `.venv/bin/dbt test` | All 26 data tests passing |
| 5. `golden_questions` | `.venv/bin/python scripts/golden.py` | Five MetricFlow comparisons on real data and on fixtures |
| 6. `audit` | `.venv/bin/python scripts/audit.py` | Model row counts and date ranges |
| 7. `dashboard_check` | `.venv/bin/python scripts/check_app.py` | Streamlit cards, cohort filter and SQL inspector execute |

The final task tests the app; it does not launch a long-running web server. Use
`make app` separately to browse the dashboard. Refresh its page after a successful DAG run.

## The concepts you can now see

**DAG:** a directed acyclic graph of tasks. In
`orchestration/dags/distribution_dbt.py`, the `>>` expression declares their order.
This example is a straight chain because the tasks share one DuckDB file.

**Task versus model:** `dbt_marts` is one Airflow task that builds five dbt models.
Airflow understands the seven workflow steps. dbt understands the SQL models and
`ref()` dependencies inside its steps. Adding a sixth mart does not require an
extra Airflow task; dbt's selection includes it automatically.

**Operator:** `BashOperator` runs the same shell commands you could type locally.
Its working directory and environment explicitly point at this project. Airflow
runs in `.airflow-venv`; dbt and MetricFlow commands use the original `.venv`.
[BashOperator reference](https://airflow.apache.org/docs/apache-airflow-providers-standard/stable/operators/bash.html).

**Scheduler and executor:** the scheduler decides which task is eligible to run;
the LocalExecutor launches it as a local process. The UI displays the recorded
results. `make airflow` uses Apache's standalone command to start the scheduler,
DAG processor, API/UI and triggerer. The triggerer is included by standalone;
these Bash tasks do not need deferrable operators.
[Apache quickstart](https://airflow.apache.org/docs/apache-airflow/stable/start.html).

**Run and task instance:** triggering creates one run. Each of the seven tasks has
an instance within that run. A second trigger adds a separate history row, while
rebuilding the same data. The cache avoids downloading the ZIP again.

**Retries and failure:** each task gets one retry after 15 seconds. A nonzero
command exit fails the task. After retries are exhausted, downstream tasks cannot
run because their upstream dependency failed. A task is not green merely because
a command started; its process must finish successfully.

**Schedule and logical date:** `schedule=None` makes this manual. There is no daily
job or backfill. The run identifier/timestamp identifies the orchestration attempt;
a manual run can have a null logical date. It never selects the SEC report date.
The input remains the fixed 2025 Q4 archive. `catchup=False` prevents catchup if you
later add a schedule, but scheduling is deliberately outside this first exercise.

**Metadata versus business data:** Airflow's local SQLite database
`.airflow/airflow.db` stores run states and scheduling metadata. Your fund data stays
in `data/lab.duckdb`. Task logs live under `.airflow/logs`. Large datasets never move
between tasks through Airflow's XCom system.

## A 15-minute exercise

1. Trigger a run. Watch its seven task states change and open `dbt_marts` logs.
   Identify the five models inside that one task.
2. Trigger a second run. Compare the `ingest_sec` logs: it uses the cached ZIP.
3. In the completed run, select `dashboard_check` and choose **Clear**. Confirm
   the selection contains only that task. Clearing resets its execution state so
   the scheduler runs the check again; it does not delete business data.
4. Read the DAG file. Find `max_active_runs=1`, `retries=1`, and the final `>>` line.
   Match each setting to what you observed in the UI.

For failure recovery practice, temporarily add a SQL file
`tests/dbt/learning_failure.sql` containing `select 1 as deliberate_failure`.
Trigger a run and inspect `dbt_tests`: dbt treats a returned test row as a failure,
Airflow retries once, and downstream tasks do not execute. Remove your temporary
test, trigger a fresh run, and confirm all tasks turn green. Restore the baseline
before using the dashboard results. You do not need to edit any production metric
or raw input for this exercise.

## Commands and troubleshooting

- `make airflow-setup`: install Airflow 3.3.1 and the standard provider in the
  separate Python 3.12 environment using the checked-in Apache constraints;
  migrate local metadata and check DAG structure. Run `make setup` first on a new clone.
- `make airflow`: start the local instance. Ctrl-C stops its components.
- `make airflow-check`: import the DAG and verify its task order, retries and limits.
- `make airflow-trigger`: unpause and enqueue a real scheduler run. Start the server
  first and allow around 10 seconds for initial DAG discovery.
- `make airflow-status`: display recorded run states.
- `make airflow-test`: execute the DAG locally for debugging. This bypasses normal
  scheduler/executor dispatch; it is different from the real UI-triggered run.
  Stop the server and other writers before using it.

If 8080 is occupied, start with `make airflow AIRFLOW_PORT=8081` and open that port.
Use the same `AIRFLOW_PORT=8081` on subsequent Airflow commands. Do not run
`make refresh`, another dbt process, or `make test` concurrently with a DAG run.
Airflow limits its own tasks/runs to one at a time; that does not lock out shell
commands or open DuckDB connections in other apps. If a task reports a DuckDB lock,
close the other connection and rerun after it releases the database.

The localhost UI uses the simple auth manager. This is a single-user macOS learning
setup with SQLite metadata, not a deployment recipe. No Docker, external database,
message broker or cloud account is required.

The constraints file came from
[Apache's versioned Python 3.12 constraints](https://raw.githubusercontent.com/apache/airflow/constraints-3.3.1/constraints-3.12.txt).
The original dbt dependency lock remains independent of Airflow.
