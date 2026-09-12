-- Include all observed dates, even historical amendments in a later ZIP.
select cast(day as date) as date_day
from generate_series(
    (select min(flow_month) from {{ ref('fact_monthly_flows') }}),
    (select max(report_date) from {{ ref('fact_fund_snapshots') }}),
    interval '1 day'
) spine(day)
