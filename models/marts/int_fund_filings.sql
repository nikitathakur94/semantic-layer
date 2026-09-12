-- A SERIES_ID identifies a fund, never a share class or an entire registrant.
select
    f.*,
    coalesce(f.series_id, 'LEI:' || nullif(f.series_lei, 'N/A'),
             'UNKNOWN:' || f.accession_number) as fund_id,
    f.series_id is null as missing_series_id,
    s.filing_date, s.report_date, s.sub_type,
    r.registrant_cik, r.registrant_name
from {{ ref('stg_fund_reported_info') }} f
left join {{ ref('stg_submission') }} s using (accession_number)
left join {{ ref('stg_registrant') }} r using (accession_number)
