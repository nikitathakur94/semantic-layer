select distinct
    accession_number,
    nullif(trim(series_id), '') as series_id,
    nullif(trim(series_lei), '') as series_lei,
    nullif(trim(series_name), '') as fund_name,
    try_cast(net_assets as decimal(36, 12)) as net_assets,
    net_assets is not null and try_cast(net_assets as decimal(36, 12)) is null as invalid_net_assets,
    {% for month in [1, 2, 3] %}
    {% for source in ['sales', 'redemption', 'reinvestment'] %}
    try_cast({{ source }}_flow_mon{{ month }} as decimal(36, 12)) as {{ source }}_mon{{ month }},
    {{ source }}_flow_mon{{ month }} is not null
        and try_cast({{ source }}_flow_mon{{ month }} as decimal(36, 12)) is null
        as invalid_{{ source }}_mon{{ month }}{{ ',' if not (loop.last and month == 3) }}
    {% endfor %}
    {% endfor %}
from {{ source('nport', 'FUND_REPORTED_INFO') }}
