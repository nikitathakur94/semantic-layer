select cast(month as varchar) as metric_time__month,
       sum(sales) as gross_sales, sum(redemptions) as redemptions,
       sum(reinvestments) as reinvestments,
       sum(sales) - sum(redemptions) as net_flows_excluding_reinvestments,
       sum(redemptions) / nullif(sum(sales),0) as redemptions_to_sales_ratio
from ref_flows where month between date '2025-07-01' and date '2025-10-31'
group by month
