-- Independent reference: query raw SEC tables, not dbt marts or semantic YAML.
-- DISTINCT ON and list unnest intentionally differ from dbt's QUALIFY/UNION.
create or replace temp view ref_filings as
select f.*, r.registrant_name, r.cik,
    coalesce(nullif(trim(f.series_id), ''),
             'LEI:' || nullif(nullif(trim(f.series_lei), ''), 'N/A'),
             'UNKNOWN:' || f.accession_number) as fund_id,
    cast(coalesce(try_strptime(s.report_date, '%d-%b-%Y'),
                  try_strptime(s.report_date, '%Y-%m-%d')) as date) as as_of,
    cast(coalesce(try_strptime(s.filing_date, '%d-%b-%Y'),
                  try_strptime(s.filing_date, '%Y-%m-%d')) as date) as filed,
    s.sub_type like '%/A' as amended
from (select distinct * from raw.FUND_REPORTED_INFO) f
left join (select distinct * from raw.SUBMISSION) s using (accession_number)
left join (select distinct * from raw.REGISTRANT) r using (accession_number);

create or replace temp view ref_funds as
select distinct on (fund_id) fund_id, series_name, registrant_name, cik,
    regexp_matches(lower(coalesce(series_name, '') || ' ' || coalesce(registrant_name, '')),
                   'franklin|templeton') as matched
from ref_filings
order by fund_id, as_of desc nulls last, filed desc nulls last, amended desc, accession_number desc;

create or replace temp view ref_snapshots as
select distinct on (fund_id, as_of) *
from ref_filings where as_of is not null
order by fund_id, as_of, filed desc nulls last, amended desc, accession_number desc;

create or replace temp view ref_flows as
select distinct on (fund_id, month) * from (
    select fund_id, accession_number, filed, amended, as_of,
        unnest([cast(date_trunc('month', as_of) - interval '2 months' as date),
                cast(date_trunc('month', as_of) - interval '1 month' as date),
                cast(date_trunc('month', as_of) as date)]) as month,
        unnest([try_cast(sales_flow_mon1 as decimal(36,12)),
                try_cast(sales_flow_mon2 as decimal(36,12)),
                try_cast(sales_flow_mon3 as decimal(36,12))]) as sales,
        unnest([try_cast(redemption_flow_mon1 as decimal(36,12)),
                try_cast(redemption_flow_mon2 as decimal(36,12)),
                try_cast(redemption_flow_mon3 as decimal(36,12))]) as redemptions,
        unnest([try_cast(reinvestment_flow_mon1 as decimal(36,12)),
                try_cast(reinvestment_flow_mon2 as decimal(36,12)),
                try_cast(reinvestment_flow_mon3 as decimal(36,12))]) as reinvestments
    from ref_snapshots
) m
order by fund_id, month, filed desc nulls last, amended desc, as_of desc, accession_number desc;
