with latest as (
    select date_trunc('month',as_of) as month, max(as_of) as as_of
    from ref_snapshots group by 1
), snapshots as (
    select latest.month, sum(try_cast(s.net_assets as decimal(36,12))) as reported_net_assets,
           count(distinct s.fund_id) as fund_count
    from ref_snapshots s join latest on s.as_of = latest.as_of group by 1
), flows as (
    select month, sum(sales) as gross_sales, sum(redemptions) as redemptions,
           sum(reinvestments) as reinvestments,
           sum(sales) - sum(redemptions) as net_flows_excluding_reinvestments,
           sum(redemptions) / nullif(sum(sales),0) as redemptions_to_sales_ratio
    from ref_flows group by month
)
select cast(coalesce(s.month,f.month) as varchar) as metric_time__month,
       s.reported_net_assets, s.fund_count, f.gross_sales, f.redemptions,
       f.reinvestments, f.net_flows_excluding_reinvestments, f.redemptions_to_sales_ratio
from snapshots s full outer join flows f using (month)
