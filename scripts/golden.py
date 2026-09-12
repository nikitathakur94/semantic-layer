"""Five questions, twice: all SEC rows and an adversarial raw-file fixture."""
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import duckdb
import pandas as pd
from pandas.testing import assert_frame_equal

q = importlib.import_module('lab.query')
ROOT = q.ROOT
sys.path.insert(0,str(ROOT / 'tests'))
from fixture import create_fixture
FLOW = ['gross_sales','redemptions','reinvestments','net_flows_excluding_reinvestments','redemptions_to_sales_ratio']
SNAP = ['reported_net_assets','fund_count']


def compare(actual, expected, name):
    assert set(actual.columns) == set(expected.columns), (name, actual.columns, expected.columns)
    keys = [n for n in expected.columns if n not in FLOW + SNAP]
    for frame in (actual,expected):
        for key in keys:
            if key.startswith('metric_time'):
                frame[key] = pd.to_datetime(frame[key]).dt.strftime('%Y-%m-%d')
            else:
                frame[key] = frame[key].fillna('<null>').astype(str)
    columns = sorted(expected.columns)
    actual = actual.sort_values(keys).reset_index(drop=True) if keys else actual
    expected = expected.sort_values(keys).reset_index(drop=True) if keys else expected
    assert_frame_equal(actual[columns],expected[columns],check_dtype=False,check_exact=False,rtol=1e-10,atol=0.01,obj=name)


def run_questions(label):
    with duckdb.connect(str(q.DB),read_only=True) as con:
        con.execute((ROOT / 'tests/reference/base.sql').read_text())
        samples = con.execute('select distinct fund_id,cik from ref_flows join ref_funds using(fund_id) '
                              'where sales is null or sales <= 0 order by fund_id limit 8').fetchall()
        funds = sorted({r[0] for r in samples})
        regs = sorted({r[1] for r in samples if r[1] is not None})
        literal = lambda values: ','.join("'"+v.replace("'","''")+"'" for v in values)
        specs = [
            ('01_latest_snapshot',SNAP,{}),
            ('02_cohort_join',FLOW,{'group_by':['fund__registrant_cik','fund__registrant_name'],'where':q.where_filter(cohort=True)}),
            ('03_month_dates',FLOW,{'group_by':['metric_time__month'],'start':'2025-07-01','end':'2025-10-31'}),
            ('04_nulls_and_filters',FLOW,{'group_by':['fund'],'where':q.where_filter(funds,regs)}),
            ('05_cross_fact_ratio',SNAP+FLOW,{'group_by':['metric_time__month']})]
        expected = []
        for name,metrics,kwargs in specs:
            sql = (ROOT / f'tests/reference/{name}.sql').read_text()
            if name.startswith('04'):
                assert funds and regs, 'Need null/zero samples to exercise filters'
                sql = sql.format(funds=literal(funds),registrants=literal(regs))
            expected.append(con.execute(sql).fetchdf())
    results=[]
    for (name,metrics,kwargs),reference in zip(specs,expected):
        actual=q.query(metrics,**kwargs)
        compare(actual,reference,name)
        results.append({'dataset':label,'question':name,'rows':len(actual),'status':'PASS'})
        print(f'PASS {label}: {name} ({len(actual)} rows)',flush=True)
    return results


if __name__ == '__main__':
    results=run_questions('SEC 2025 Q4')
    with tempfile.TemporaryDirectory() as directory:
        project=Path(directory)
        for name in ['dbt_project.yml','profiles.yml']:
            shutil.copyfile(ROOT/name,project/name)
        shutil.copytree(ROOT/'models',project/'models')
        shutil.copytree(ROOT/'tests/dbt',project/'tests/dbt')
        db=project/'lab.duckdb'
        create_fixture(db)
        result=subprocess.run([str(Path(sys.executable).parent/'dbt'),'build'],cwd=project,
            env={**os.environ,'DBT_PROFILES_DIR':str(project),'LAB_DB_PATH':str(db)},capture_output=True,text=True)
        if result.returncode:
            raise RuntimeError(result.stdout+result.stderr)
        q.ROOT,q.DB,q.MANIFEST=project,db,project/'target/semantic_manifest.json'
        results+=run_questions('adversarial fixture')
        with duckdb.connect(str(db),read_only=True) as con:
            assert con.execute('select count(*) from fact_fund_snapshots').fetchone()[0] == 6
            assert con.execute('select count(*) from fact_monthly_flows').fetchone()[0] == 16
            assert con.execute("select sales from fact_monthly_flows where fund_id='A' and flow_month='2025-09-01'").fetchone()[0] is None
        print('PASS fixture: 6 snapshots, 16 months, winning amendment null preserved')
    (ROOT/'data/golden_results.json').write_text(json.dumps(results,indent=2))
