select fund_id, flow_month
from {{ ref('fact_monthly_flows') }}
group by fund_id, flow_month having count(*) > 1
