-- Fail instead of silently losing a fund or multiplying an accession join.
select f.accession_number
from {{ ref('int_fund_filings') }} f
where report_date is null or filing_date is null
union all
select accession_number
from {{ ref('int_fund_filings') }}
group by accession_number having count(*) <> 1
