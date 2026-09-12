-- Current-in-this-extract names, not a historical ownership dimension.
select fund_id, series_id, series_lei, fund_name, registrant_cik, registrant_name,
       missing_series_id,
       case when regexp_matches(lower(coalesce(fund_name, '') || ' ' ||
                                      coalesce(registrant_name, '')), 'franklin|templeton')
            then 'Franklin / Templeton name match' else 'Other names' end as cohort
from {{ ref('int_fund_filings') }}
qualify row_number() over (
    partition by fund_id
    order by report_date desc nulls last, filing_date desc nulls last,
             (sub_type like '%/A') desc, accession_number desc
) = 1
