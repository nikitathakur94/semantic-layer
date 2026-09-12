"""Prove the installed CLI can compile AND execute a local DuckDB metric."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BIN = Path(sys.executable).parent
with tempfile.TemporaryDirectory() as tmp:
    env = {**os.environ, 'DBT_PROFILES_DIR': str(ROOT),
           'LAB_DB_PATH': f'{tmp}/smoke.duckdb', 'DBT_SEND_ANONYMOUS_USAGE_STATS': 'false'}
    project = ROOT / 'tests/smoke'
    subprocess.run([str(BIN / 'dbt'), 'build'], cwd=project, env=env, check=True)
    subprocess.run([str(BIN / 'mf'), 'query', '--metrics', 'smoke_total',
                    '--csv', f'{tmp}/result.csv'], cwd=project, env=env, check=True)
    import csv
    with open(f'{tmp}/result.csv') as f:
        assert float(next(csv.DictReader(f))['smoke_total']) == 42
    print('PASS: real mf query returned smoke_total = 42')
