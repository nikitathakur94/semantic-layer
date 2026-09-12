select flow_id from {{ ref('fact_monthly_flows') }}
where (sales < 0 or redemptions < 0 or reinvestments < 0)
      and questionable_flow_sign is distinct from true
