"""Persist source/model audit evidence; no business-metric formulas here."""
import json
from pathlib import Path
import duckdb
from lab.query import DB, ROOT

with duckdb.connect(str(DB), read_only=True) as con:
    counts = {name: con.execute(f'select count(*) from {name}').fetchone()[0]
              for name in ['dim_fund', 'fact_fund_snapshots', 'fact_monthly_flows']}
    dates = con.execute('select min(report_date), max(report_date) from fact_fund_snapshots').fetchone()
    flows = con.execute('select min(flow_month), max(flow_month) from fact_monthly_flows').fetchone()
    counts['snapshot_candidates_removed'] = con.execute('select (select count(*) from int_fund_filings) - (select count(*) from fact_fund_snapshots)').fetchone()[0]
    counts['overlapping_months_removed'] = counts['fact_fund_snapshots'] * 3 - counts['fact_monthly_flows']
    counts['missing_series_id_funds'] = con.execute('select count(*) from dim_fund where missing_series_id').fetchone()[0]
    counts['name_matched_cohort_funds'] = con.execute("select count(*) from dim_fund where cohort = 'Franklin / Templeton name match'").fetchone()[0]
audit = {'row_counts':counts, 'snapshot_range':list(map(str,dates)), 'flow_range':list(map(str,flows))}
(ROOT / 'data/model_audit.json').write_text(json.dumps(audit, indent=2))
print(json.dumps(audit, indent=2))
