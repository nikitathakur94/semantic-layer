-- One row per fund and actual report date. A later filing supersedes an earlier
-- one; on the same filing day prefer an amendment, then accession as tie-break.
select *,
    fund_id || ':' || cast(report_date as varchar) as snapshot_id,
    net_assets < 0 as questionable_net_assets_sign
from {{ ref('int_fund_filings') }}
where report_date is not null
qualify row_number() over (
    partition by fund_id, report_date
    order by filing_date desc nulls last, (sub_type like '%/A') desc,
             accession_number desc
) = 1
