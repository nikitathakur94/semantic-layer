select fund_id as fund,
       sum(sales) as gross_sales, sum(redemptions) as redemptions,
       sum(reinvestments) as reinvestments,
       sum(sales) - sum(redemptions) as net_flows_excluding_reinvestments,
       sum(redemptions) / nullif(sum(sales),0) as redemptions_to_sales_ratio
from ref_flows join ref_funds using (fund_id)
where fund_id in ({funds}) and cik in ({registrants})
group by fund_id
