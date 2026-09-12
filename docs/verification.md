# Local verification

On 2026-09-12, Python 3.12.8 (macOS ARM64) executed the isolated
`scripts/smoke.py`: dbt built two tables, then a real `mf query --metrics
smoke_total --csv ...` returned **42**. This gate passed before SEC pipeline
implementation. `make setup` repeats this gate on each machine. All resolved
packages are pinned in requirements.txt; direct dependencies are in requirements.in.
