"""The dashboard's sole metric gateway: an argument-safe, cached mf CLI call."""
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
DB = Path(os.environ.get('LAB_DB_PATH', ROOT / 'data/lab.duckdb')).resolve()
MF = Path(sys.executable).parent / 'mf'
MANIFEST = ROOT / 'target/semantic_manifest.json'


def catalog():
    return {m['name']: m for m in yaml.safe_load((ROOT / 'models/semantic.yml').read_text())['metrics']}


def fingerprint():
    if not MANIFEST.exists() or not DB.exists():
        raise RuntimeError('Run make refresh first.')
    # Refuse stale definitions; do not show new YAML labels over old results.
    manifest_time = MANIFEST.stat().st_mtime_ns
    if any(p.stat().st_mtime_ns > manifest_time for p in (ROOT / 'models').rglob('*.yml')):
        raise RuntimeError('Metric definitions changed. Run make parse, then rerun the app.')
    return hashlib.sha256(MANIFEST.read_bytes() +
        f'{DB}:{DB.stat().st_mtime_ns}:{DB.stat().st_size}'.encode()).hexdigest()


def where_filter(funds=(), registrants=(), cohort=False):
    """Values become escaped SQL literals; subprocess never invokes a shell."""
    def literals(values):
        return ', '.join("'" + str(v).replace("'", "''") + "'" for v in values)
    clauses = []
    if funds:
        clauses.append("{{ Entity('fund') }} in (" + literals(funds) + ')')
    if registrants:
        clauses.append("{{ Dimension('fund__registrant_cik') }} in (" + literals(registrants) + ')')
    if cohort:
        clauses.append("{{ Dimension('fund__cohort') }} = 'Franklin / Templeton name match'")
    return ' and '.join(clauses)


def query(metrics, group_by=(), start=None, end=None, where='', order=(), limit=None, explain=False):
    known = catalog()
    if not metrics or any(m not in known for m in metrics):
        raise ValueError('Unknown or empty metric list')
    for value in (*group_by, *(v.lstrip('-') for v in order)):
        if not re.fullmatch(r'[a-z][a-z0-9_]*', value):
            raise ValueError('Invalid dimension/order identifier')
    args = [str(MF), 'query', '--metrics', ','.join(metrics), '--quiet']
    for flag, value in [('--group-by', ','.join(group_by)), ('--where', where),
                        ('--order', ','.join(order))]:
        if value:
            args += [flag, value]
    for flag, value in [('--start-time', start), ('--end-time', end)]:
        if value:
            args += [flag, date.fromisoformat(str(value)).isoformat()]
    if limit is not None:
        if int(limit) < 1:
            raise ValueError('Limit must be positive')
        args += ['--limit', str(int(limit))]
    key = hashlib.sha256(json.dumps([fingerprint(), args, explain]).encode()).hexdigest()
    cache = ROOT / 'data/query_cache'
    cache.mkdir(parents=True, exist_ok=True)
    destination = cache / (key + ('.sql' if explain else '.csv'))
    if not destination.exists():
        with tempfile.TemporaryDirectory(dir=cache) as tmp:
            output = Path(tmp) / 'result.csv'
            command = args + (['--explain'] if explain else ['--csv', str(output)])
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                timeout=120, env={**os.environ, 'DBT_PROFILES_DIR': str(ROOT),
                                 'LAB_DB_PATH': str(DB), 'DBT_SEND_ANONYMOUS_USAGE_STATS': 'false'})
            if result.returncode:
                raise RuntimeError(f'mf query failed:\n{result.stdout}\n{result.stderr}')
            if explain:
                sql = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout)
                match = re.search(r'(?m)^(?:WITH|SELECT)\b', sql)
                if not match:
                    raise RuntimeError(f'No generated SQL in mf output: {sql}')
                output.write_text(sql[match.start():].strip())
            if not output.exists():
                raise RuntimeError('MetricFlow did not produce its CSV output.')
            output.replace(destination)
    return destination.read_text() if explain else pd.read_csv(
        destination, dtype={name: 'string' for name in group_by},
        keep_default_na=False, na_values=[''])
