select distinct
    accession_number,
    nullif(trim(cik), '') as registrant_cik,
    nullif(trim(registrant_name), '') as registrant_name
from {{ source('nport', 'REGISTRANT') }}
