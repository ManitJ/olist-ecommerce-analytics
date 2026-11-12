"""The Streamlit preview runs without exceptions and shows reconciled headline values."""
import json

from conftest import ROOT, integration
from olist_ba.config import OUTPUTS


@integration
def test_streamlit_preview_runs_and_reconciles():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / "dashboard" / "streamlit" / "app.py"), default_timeout=180).run()
    assert not at.exception
    m = {x.label: x.value for x in at.metric}
    km = json.loads((OUTPUTS / "key_metrics.json").read_text())
    assert m["Late delivery rate"] == f"{km['late_rate']:.1%}"
    assert m["Late orders avoided / yr"] == f"{km['scenario_base_late_orders_avoided']:,}"
    assert m["Scenario late rate"] == f"{km['scenario_base_new_late_rate']:.2%}"
