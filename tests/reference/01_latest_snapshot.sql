select sum(try_cast(net_assets as decimal(36,12))) as reported_net_assets,
       count(distinct fund_id) as fund_count
from ref_snapshots where as_of = (select max(as_of) from ref_snapshots)
