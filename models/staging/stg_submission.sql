-- Exact duplicate rows are harmless; conflicting accession rows fail tests.
select distinct
    accession_number,
    cast(coalesce(try_strptime(filing_date, '%d-%b-%Y'),
                  try_strptime(filing_date, '%Y-%m-%d')) as date) as filing_date,
    cast(coalesce(try_strptime(report_date, '%d-%b-%Y'),
                  try_strptime(report_date, '%Y-%m-%d')) as date) as report_date,
    sub_type,
    report_ending_period as fiscal_year_end_raw
from {{ source('nport', 'SUBMISSION') }}
