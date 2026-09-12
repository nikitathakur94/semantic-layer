# Modeling decisions and limitations

## Scope and provenance

This lab ingests every row of SUBMISSION, REGISTRANT and FUND_REPORTED_INFO from
the official **2025 Q4 filing extract**. It extracts no holdings, share-class returns,
or other tables. The ZIP remains cached in full. Raw columns remain VARCHAR so
identifiers retain leading zeros and original malformed values remain inspectable.
Blank source fields become SQL NULL. Staging parses dates and DECIMAL(36,12)
amounts; nonblank unparseable amounts become null with an explicit invalid-value flag.

`data/ingestion_manifest.json` records source URLs, UTC download/ingestion timestamps,
server Last-Modified, archive size/SHA-256 and actual raw row counts. Manual ZIP
imports record their import time and leave download time unknown. The cache sidecar
preserves the original download provenance on subsequent refreshes.

The SEC describes this as public, as-filed data, including amendments. The quarter
is a dissemination window, not a restriction on report dates. Missing nonpublic
filings, missing products, funds-of-funds duplication, and incomplete corporate
relationships prevent interpreting the total as corporate AUM. See the
[official dataset page](https://www.sec.gov/data-research/sec-markets-data/form-n-port-data-sets)
and [table dictionary](https://www.sec.gov/files/nport_readme.pdf).

## Identity and amendment policy

1. Identify the fund by SERIES_ID, otherwise SERIES_LEI (excluding `N/A`), otherwise
   `UNKNOWN:` plus accession. Preserve all funds, including incomplete identities.
   `missing_series_id` explicitly marks fallback identities; accession fallbacks
   cannot establish continuity across filings and can overcount economic funds.
2. Remove only exact duplicates in each staging model. Conflicting rows with the
   same accession fail uniqueness tests. Required accession relationships fail
   before downstream joins are accepted.
3. Keep one snapshot per fund and REPORT_DATE. Sort by FILING_DATE descending,
   prefer `/A` on the same filing day, then use accession descending as a stable
   tie-break. The data lacks acceptance timestamps; same-day precedence is a lab
   convention, not proof of exact intraday ordering.
4. Map MON1, MON2 and MON3 to the report month minus two, minus one, and the report
   month. Use calendar-month starts for flow keys. REPORT_ENDING_PERIOD is fiscal
   year-end and never participates in this calculation. A report on August 29
   still maps MON3 to August 1.
5. Among overlapping fund/month candidates from retained snapshots, the latest
   FILING_DATE wins, then amendment flag, latest REPORT_DATE and accession. Keep
   the winning row intact, even when it replaces a value with null. Never stitch
   fields from multiple reports. This convention prioritizes newly filed evidence;
   a late amendment can supersede an overlap from a later report date.
6. `dim_fund` keeps the latest available name and registrant for each identity;
   these are current-in-extract attributes, not historical ownership relationships.

## Time, nulls and signs

Reported net assets and fund count use MetricFlow's `non_additive_dimension`,
`window_choice: max`, with no per-fund carry-forward. For each requested time
bucket, select the latest actual report date in that bucket, then aggregate only
that date. A query over a year does not sum monthly snapshots. A fund without a
snapshot on the selected date contributes nothing; a fund with null net assets
still contributes to fund count. Use an exact snapshot date when comparing groups
or rankings, so the reporting date cannot vary between groups.

The app defaults to September 30, 2025, the largest reporting-date population in
this extract. It offers every observed report date and labels the exact card date.
Snapshot trends show individual dates and reporting counts; do not sum the points.
November 30 has only two reporting funds. All-date trend populations vary.

Flow measures sum non-null observations. An all-null total stays null; there is no
`coalesce(..., 0)`. Net flows subtract the two separately reported totals, and the
ratio divides those totals. If only some observations are missing, both results
are partial and their component coverage may differ. The paired-flow coverage
metric reveals whether sales and redemptions are both present on the same rows.
Zero sales produces an undefined (null) ratio. A null result is displayed as a dash.
Negative sales, redemptions, reinvestments or net assets are retained and counted
as questionable signs, not corrected with ABS or sign flipping.

Gross sales exclude reinvestments under Form N-PORT Item B.6.a. The filing definition
includes exchanges and can reflect omnibus netting and acquisition activity; it
is not a clean measure of organic distribution demand. See
[Form N-PORT, Item B.6](https://www.sec.gov/files/formn-port.pdf).

## Cohort and coverage

The cohort is a case-insensitive `franklin|templeton` substring match in the latest
fund OR registrant name. It includes 218 identities in the downloaded extract.
It can miss affiliates whose names do not match and include false positives. It
is neither a corporate family mapping nor complete Franklin Templeton coverage.

Coverage ratios divide present-value observations by observed snapshot rows or
fund-month rows. They do not measure missing filings, industry share, product
coverage, or corporate-family completeness. Quality counts come from semantic
metrics too. `data/model_audit.json` separately records discarded candidates,
identity gaps and model row counts for pipeline auditing.

## Validation

`tests/reference` contains independent SQL reading raw tables with DISTINCT ON
selection and list unnesting. It does not read dbt marts or YAML formulas. Five
questions compare it to actual `mf query` CSVs, first on all real SEC rows and then
on a tiny adversarial fixture. The fixture guarantees exact source duplicates,
amendments, overlapping months, a late winning null, unequal fund ratios, zero
sales, negative signs, different dates and a shared registrant.

The questions are: latest-date assets/count; joined cohort flows by registrant;
calendar-month flows in a bounded interval; selected funds/registrants with missing
or zero sales; and monthly multi-fact metrics with ratios of totals. Tolerance is
1 cent absolute / 1e-10 relative for CSV floating-point amounts. Identifiers and
null locations must match. These are lab checks, not external certification.

MetricFlow's pinned v1-compatible YAML uses measures and semantic_models. The
[current dbt measure reference](https://docs.getdbt.com/docs/build/measures) documents
the non-additive settings; do not migrate this lab to the v2 syntax without
changing the pins and rerunning the CLI gate and golden suite.
