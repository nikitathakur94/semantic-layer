with months as (
    {% for month in [1, 2, 3] %}
    select fund_id, accession_number, report_date, filing_date, sub_type,
        {{ month }} as source_month,
        cast(date_trunc('month', report_date) - interval '{{ 3 - month }} months' as date) as flow_month,
        sales_mon{{ month }} as sales,
        redemption_mon{{ month }} as redemptions,
        reinvestment_mon{{ month }} as reinvestments,
        invalid_sales_mon{{ month }} or invalid_redemption_mon{{ month }}
            or invalid_reinvestment_mon{{ month }} as invalid_flow_value
    from {{ ref('fact_fund_snapshots') }}
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
)
select *, fund_id || ':' || cast(flow_month as varchar) as flow_id,
       sales < 0 or redemptions < 0 or reinvestments < 0 as questionable_flow_sign,
       sales is not null and redemptions is not null as paired_flow_present
from months
-- Overlapping report windows: latest filed information wins, then latest report.
-- Keep the winning row intact, including its nulls; never fill from older rows.
qualify row_number() over (
    partition by fund_id, flow_month
    order by filing_date desc nulls last, (sub_type like '%/A') desc,
             report_date desc, accession_number desc
) = 1
