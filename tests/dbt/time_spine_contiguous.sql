select 1
from {{ ref('metricflow_time_spine') }}
having count(*) <> date_diff('day', min(date_day), max(date_day)) + 1
