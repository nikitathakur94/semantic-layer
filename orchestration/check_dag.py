"""Fast DAG import/structure check without running SEC or dbt commands."""
import os
from airflow.dag_processing.dagbag import DagBag

bag = DagBag(dag_folder=os.environ['AIRFLOW__CORE__DAGS_FOLDER'])
assert not bag.import_errors, bag.import_errors
dag = bag.get_dag('distribution_dbt')
assert dag is not None
expected = ['ingest_sec', 'dbt_staging', 'dbt_marts', 'dbt_tests',
            'golden_questions', 'audit', 'dashboard_check']
assert [task.task_id for task in dag.topological_sort()] == expected
assert dag.max_active_runs == dag.max_active_tasks == 1
for i, name in enumerate(expected):
    task = dag.get_task(name)
    assert task.downstream_task_ids == set(expected[i + 1:i + 2])
    assert task.retries == 1
    assert task.trigger_rule == 'all_success'
print('PASS: seven-task DAG imports; dependencies, retries and single-run limits verified')
