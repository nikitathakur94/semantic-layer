# Local verification

On 2026-09-12, Python 3.12.8 (macOS ARM64) executed the isolated
`scripts/smoke.py`: dbt built two tables, then a real `mf query --metrics
smoke_total --csv ...` returned **42**. This gate passed before SEC pipeline
implementation. `make setup` repeats this gate on each machine. All resolved
packages are pinned in requirements.txt; direct dependencies are in requirements.in.

## Completed pipeline run

Executed on macOS ARM64 on 2026-09-12:

| Check | Result |
| --- | --- |
| `make setup` | PASS: locked installation, pip check, real `mf query` = 42 |
| `make refresh` | PASS: official download first, cached repeat, all models built |
| `make test` | PASS: 26 dbt tests; 5 Python tests; 5 golden questions × 2 datasets; Streamlit AppTest |
| `make app` | PASS: HTTP health `ok` and live browser-rendered dashboard on port 8502 |
| README metric-edit exercise | PASS: YAML edit + `make parse` changed the dashboard; restored baseline afterward |

Streamlit checks executed real MetricFlow subprocesses and rendered seven KPI cards,
trends and rankings. The name-matched cohort filter and generated SQL inspector
were exercised. Live browser inspection led to a 3+2 flow-card layout so numbers
and labels fit at the tested 1280-pixel viewport. Port 8501 belonged to an existing
app; this project uses 8502 without interrupting it. Startup is headless to avoid
Streamlit's optional email prompt.

## Download and model evidence

- [Source page](https://www.sec.gov/data-research/sec-markets-data/form-n-port-data-sets)
- [Official ZIP](https://www.sec.gov/files/dera/data/form-n-port-data-sets/2025q4_nport.zip)
- Downloaded: 2026-09-12 16:48:49 UTC
- Server Last-Modified: 2026-01-07 14:46:14 GMT
- Archive size: 417,802,295 bytes
- SHA-256: `4ebb169e6cc0745b4cc65de4e83ea4916c7ad39146c383007e078b6223af8dea`

| Table / audit | Actual rows |
| --- | ---: |
| raw.SUBMISSION | 13,328 |
| raw.REGISTRANT | 13,328 |
| raw.FUND_REPORTED_INFO | 13,328 |
| dim_fund | 13,244 |
| fact_fund_snapshots | 13,303 |
| fact_monthly_flows | 39,893 |
| Superseded snapshot candidates | 25 |
| Overlapping monthly candidates removed | 16 |
| Funds missing SERIES_ID (fallback identity used) | 688 |
| Franklin / Templeton name-matched identities | 218 |

Snapshot dates span 2024-12-31–2025-11-30; flow months span 2024-10-01–2025-11-01.
The default 2025-09-30 snapshot contains 6,625 funds. The latest snapshot date has
only two. These counts describe the downloaded extract, not an external universe.

The five golden comparisons returned respectively 1, 50, 4, 8 and 14 rows on the
SEC data, and 1, 1, 4, 4 and 4 rows on the adversarial fixture. The fixture retained
6 snapshots and 16 fund-months; its latest overlapping September sales value stayed
NULL. Dollar comparisons use one-cent absolute / 1e-10 relative tolerance; ratios
use 1e-12 absolute tolerance. CSV identifier leading zeros are preserved.

The exercise used the default July–November flow interval. Temporarily including
reinvestments changed the card from **−$121.34B** to **+$16.76B**, with a changed label.
No dashboard formula was edited. The original expression was restored and reparsed.

Local, ignored evidence files: `data/ingestion_manifest.json`, `data/model_audit.json`,
`data/golden_results.json`, `data/setup_verified.log`, `data/refresh.log`,
`data/test_verified.log`, `data/exercise_verified.log` and `data/app_server.log`.
