select distinct fund_id from {{ ref('int_fund_filings') }}
except
select fund_id from {{ ref('dim_fund') }}
