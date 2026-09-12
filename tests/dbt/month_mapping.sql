select * from {{ ref('fact_monthly_flows') }}
where flow_month <> cast(date_trunc('month', report_date)
                        - (3 - source_month) * interval '1 month' as date)
   or flow_month > report_date
   or source_month not between 1 and 3
