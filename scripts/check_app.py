"""Execute Streamlit, including its actual MetricFlow subprocesses."""
from pathlib import Path
from streamlit.testing.v1 import AppTest

root = Path(__file__).resolve().parents[1]
app = AppTest.from_file(str(root / 'app.py'), default_timeout=120).run()
assert not app.exception, app.exception
assert not app.error, [e.value for e in app.error]
assert len(app.metric) == 7, f'Expected seven metric cards, got {len(app.metric)}'
app.checkbox[0].check().run()
assert not app.exception and not app.error
next(s for s in app.selectbox if s.label == 'Inspect metric').select('redemptions_to_sales_ratio').run()
app.button[0].click().run()
assert not app.exception and not app.error
assert any('SELECT' in c.value for c in app.code), 'SQL inspector did not render SQL'
print('PASS: dashboard rendered seven cards, cohort filter, and generated SQL')
