"""Run with make app. All displayed metrics come from lab.query → mf query."""
from datetime import date
import duckdb
import pandas as pd
import streamlit as st

from lab.query import DB, catalog, fingerprint, query, where_filter

st.set_page_config(page_title='Distribution Semantics Lab', page_icon='◈', layout='wide')
st.title('Distribution Semantics Lab')
st.caption('SEC N-PORT · 2025 Q4 filing extract · USD · educational metrics')
st.info('Reported fund net assets are not corporate AUM. This public filing subset excludes '
        'other products and may include funds investing in other funds. Do not infer firm-wide assets.')


@st.cache_data(show_spinner=False)
def filter_options(version):
    # Dimension members only. Never fetch or calculate a business metric here.
    with duckdb.connect(str(DB), read_only=True) as con:
        funds = con.execute('select fund_id, fund_name, registrant_cik, registrant_name, cohort '
                            'from dim_fund order by fund_name').fetchdf()
        snapshots = [r[0] for r in con.execute('select distinct report_date from fact_fund_snapshots '
                                              'order by report_date').fetchall()]
        months = [r[0] for r in con.execute('select distinct flow_month from fact_monthly_flows '
                                          'order by flow_month').fetchall()]
    return funds, snapshots, months


def value(frame, metric):
    return frame.iloc[0][metric] if not frame.empty else None


def formatted(number, units):
    if number is None or pd.isna(number):
        return '—'
    if units == 'ratio':
        return f'{number:.1%}'
    if units == 'USD':
        sign = '-' if number < 0 else ''
        amount = abs(number)
        if amount >= 1e12:
            return f'{sign}${amount / 1e12:,.2f}T'
        return f'{sign}${amount / 1e9:,.2f}B' if amount >= 1e9 else f'{sign}${amount:,.0f}'
    return f'{number:,.0f}'


try:
    definitions = catalog()
    funds, snapshot_dates, months = filter_options(fingerprint())
    with st.sidebar:
        st.header('Reporting scope')
        cohort = st.checkbox('Franklin / Templeton name match')
        st.caption('Incomplete family coverage: names only; misses affiliates with other names '
                   'and can include false matches. No ownership mapping is asserted.')
        eligible = funds[funds.cohort == 'Franklin / Templeton name match'] if cohort else funds
        regs = eligible.dropna(subset=['registrant_cik']).drop_duplicates('registrant_cik')
        reg_labels = dict(zip(regs.registrant_cik, regs.registrant_name))
        registrants = st.multiselect('Registrant', list(reg_labels),
                                     format_func=lambda k: f'{reg_labels[k]} · {k}')
        eligible = eligible[eligible.registrant_cik.isin(registrants)] if registrants else eligible
        fund_labels = dict(zip(eligible.fund_id, eligible.fund_name))
        selected_funds = st.multiselect('Fund', list(fund_labels),
                                        format_func=lambda k: f'{fund_labels[k]} · {k}')
        preferred = date(2025, 9, 30)
        snapshot = st.selectbox('Snapshot date', snapshot_dates,
                               index=snapshot_dates.index(preferred) if preferred in snapshot_dates else len(snapshot_dates)-1)
        start, end = st.select_slider('Flow months (inclusive)', options=months,
            value=(date(2025, 7, 1) if date(2025, 7, 1) in months else months[0], months[-1]))
        st.caption('Flow dates describe observation months, not filing dates. Older amendments '
                   'can appear in this Q4 extract. Snapshot cards use one exact date; no carry-forward.')
    where = where_filter(selected_funds, registrants, cohort)
    snapshot_metrics = ['reported_net_assets', 'fund_count']
    flow_metrics = ['gross_sales', 'redemptions', 'reinvestments',
                    'net_flows_excluding_reinvestments', 'redemptions_to_sales_ratio']
    snap_quality = ['snapshot_observations','net_assets_present','net_assets_coverage',
                    'negative_net_assets_observations','invalid_net_assets_observations']
    flow_quality = ['flow_observations','sales_present','redemptions_present','reinvestments_present',
                    'paired_flows_present','sales_coverage','redemptions_coverage','reinvestments_coverage',
                    'paired_flows_coverage','negative_flow_observations','invalid_flow_observations']
    with st.spinner('Querying governed metrics…'):
        snap = query(snapshot_metrics + snap_quality, start=snapshot, end=snapshot, where=where)
        flow = query(flow_metrics + flow_quality, start=start, end=end, where=where)
    st.subheader(f'Reported snapshots · {snapshot:%d %b %Y}')
    for col, name in zip(st.columns(2), snapshot_metrics):
        col.metric(definitions[name]['label'], formatted(value(snap, name), definitions[name]['config']['meta']['units']))
    st.subheader(f'Monthly flows · {start:%b %Y}–{end:%b %Y}')
    for names in (flow_metrics[:3], flow_metrics[3:]):
        for col, name in zip(st.columns(len(names)), names):
            col.metric(definitions[name]['label'], formatted(value(flow, name), definitions[name]['config']['meta']['units']))
    st.caption('A dash means unavailable, including a zero sales denominator. Totals use reported '
               'non-null values; sales and redemptions may have different coverage. Negative inputs remain as filed.')

    st.subheader('Missing-data coverage')
    rows = []
    for name, frame in [('net_assets_coverage',snap),('sales_coverage',flow),
                        ('redemptions_coverage',flow),('reinvestments_coverage',flow),('paired_flows_coverage',flow)]:
        rows.append({'Coverage':definitions[name]['label'],'Present / observed':formatted(value(frame,name),'ratio')})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')
    st.caption('Coverage is field completeness among observed fund rows/months, not completeness '
               'of the industry or Franklin/Templeton family. Funds without filings are not observable here.')
    with st.expander('Observation counts and quality flags'):
        st.dataframe(snap[snap_quality], hide_index=True)
        st.dataframe(flow[flow_quality], hide_index=True)

    st.subheader('Trends')
    left, right = st.columns(2)
    with left:
        st.caption('All reported dates: net assets by exact report date · populations vary; points are not additive')
        trend = query(snapshot_metrics, group_by=['metric_time__day'], where=where,
                      order=['metric_time__day'])
        trend['metric_time__day'] = pd.to_datetime(trend['metric_time__day'])
        st.line_chart(trend.set_index('metric_time__day')[['reported_net_assets']])
        with st.expander('Reporting fund count at each date'):
            st.dataframe(trend, hide_index=True)
    with right:
        st.caption('Selected monthly flows · USD')
        trend = query(flow_metrics, group_by=['metric_time__month'], start=start,end=end,
                      where=where,order=['metric_time__month'])
        trend['metric_time__month'] = pd.to_datetime(trend['metric_time__month'])
        st.line_chart(trend.set_index('metric_time__month')[['gross_sales','redemptions','net_flows_excluding_reinvestments']])
    st.subheader('Fund rankings')
    ranking = st.selectbox('Rank funds by', snapshot_metrics + flow_metrics,
                          format_func=lambda k: definitions[k]['label'])
    rank_start, rank_end = (snapshot,snapshot) if ranking in snapshot_metrics else (start,end)
    ranked = query([ranking],group_by=['fund','fund__fund_name','fund__registrant_name'],
                   start=rank_start,end=rank_end,where=where,order=['-'+ranking],limit=20)
    st.dataframe(ranked.rename(columns={'fund':'Fund ID','fund__fund_name':'Fund',
        'fund__registrant_name':'Registrant',ranking:definitions[ranking]['label']}),
        hide_index=True,width='stretch')

    st.subheader('Definitions and generated SQL')
    chosen = st.selectbox('Inspect metric',snapshot_metrics + flow_metrics,
                         format_func=lambda k: definitions[k]['label'])
    definition = definitions[chosen]
    st.write(definition['description'])
    st.json(definition['config']['meta'])
    st.code(__import__('yaml').safe_dump(definition,sort_keys=False),language='yaml')
    if st.button('Show generated SQL'):
        sql_start,sql_end = (snapshot,snapshot) if chosen in snapshot_metrics else (start,end)
        st.code(query([chosen],start=sql_start,end=sql_end,where=where,explain=True),language='sql')
except (RuntimeError, duckdb.Error) as error:
    st.error(str(error))
    st.stop()
