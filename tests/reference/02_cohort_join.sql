select d.cik as fund__registrant_cik, d.registrant_name as fund__registrant_name,
       sum(sales) as gross_sales, sum(redemptions) as redemptions,
       sum(reinvestments) as reinvestments,
       sum(sales) - sum(redemptions) as net_flows_excluding_reinvestments,
       sum(redemptions) / nullif(sum(sales),0) as redemptions_to_sales_ratio
from ref_flows f join ref_funds d using (fund_id)
where d.matched
group by d.cik, d.registrant_name
