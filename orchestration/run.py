"""Keep this lab's Airflow config, metadata, credentials and logs inside the repo."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
AIRFLOW_HOME = ROOT / '.airflow'
PORT = os.environ.get('AIRFLOW_PORT', '8080')


def environment():
    return {
        **os.environ,
        'AIRFLOW_HOME': str(AIRFLOW_HOME),
        'PATH': str(ROOT / '.airflow-venv/bin') + os.pathsep + os.environ.get('PATH', ''),
        'LAB_PROJECT_ROOT': str(ROOT),
        'AIRFLOW__CORE__DAGS_FOLDER': str(ROOT / 'orchestration/dags'),
        'AIRFLOW__CORE__LOAD_EXAMPLES': 'false',
        'AIRFLOW__CORE__EXECUTOR': 'LocalExecutor',
        'AIRFLOW__CORE__PARALLELISM': '1',
        'AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_USERS': 'learner:admin',
        'AIRFLOW__DATABASE__SQL_ALCHEMY_CONN': f'sqlite:///{AIRFLOW_HOME / "airflow.db"}',
        'AIRFLOW__API__HOST': '127.0.0.1',
        'AIRFLOW__API__PORT': PORT,
        'AIRFLOW__API__BASE_URL': f'http://localhost:{PORT}',
        'AIRFLOW__CORE__EXECUTION_API_SERVER_URL': f'http://localhost:{PORT}/execution/',
        'AIRFLOW__DAG_PROCESSOR__REFRESH_INTERVAL': '10',
        'AIRFLOW__DAG_PROCESSOR__MIN_FILE_PROCESS_INTERVAL': '10',
        # macOS forked workers can otherwise abort in Apple's system frameworks.
        'OBJC_DISABLE_INITIALIZE_FORK_SAFETY': 'YES',
        'NO_PROXY': 'localhost,127.0.0.1',
    }


if __name__ == '__main__':
    AIRFLOW_HOME.mkdir(mode=0o700, exist_ok=True)
    args = sys.argv[1:]
    binary = ROOT / '.airflow-venv/bin/airflow'
    if args == ['check']:
        binary = ROOT / '.airflow-venv/bin/python'
        args = [str(ROOT / 'orchestration/check_dag.py')]
    if not binary.exists():
        raise SystemExit('Run make airflow-setup first.')
    os.execve(str(binary), [str(binary), *args], environment())
