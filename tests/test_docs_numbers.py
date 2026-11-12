"""Anti-fabrication check: headline numbers quoted in the README and executive reports must match
the pipeline's outputs (outputs/key_metrics.json). If the data or logic changes, this test fails
until the prose is updated."""
import json

import pytest

from conftest import ROOT
from olist_ba.config import OUTPUTS

KM = json.loads((OUTPUTS / "key_metrics.json").read_text()) if (OUTPUTS / "key_metrics.json").exists() else None
DOCS = {p: (ROOT / p).read_text() for p in ["README.md", "reports/executive_memo.md", "reports/executive_summary.md",
                                             "docs/06_insights_and_evidence.md"]}

pct0 = lambda x: f"{x * 100:.0f}%"   # noqa: E731
pct1 = lambda x: f"{x * 100:.1f}%"   # noqa: E731
pct2 = lambda x: f"{x * 100:.2f}%"   # noqa: E731

# (metric key, formatter, documents that must contain the formatted value)
CLAIMS = [
    ("late_rate", pct1, ["README.md", "reports/executive_memo.md", "reports/executive_summary.md"]),
    ("low_review_late", pct0, ["README.md", "reports/executive_memo.md", "reports/executive_summary.md"]),
    ("low_review_on_time", pct0, ["README.md", "reports/executive_memo.md", "reports/executive_summary.md"]),
    ("share_late_post_handoff", pct0, ["README.md", "reports/executive_memo.md", "reports/executive_summary.md"]),
    ("top15_lanes_share_of_excess_late", pct0, ["README.md", "reports/executive_memo.md", "reports/executive_summary.md"]),
    ("top15_lanes_share_of_volume", pct0, ["README.md", "reports/executive_memo.md", "reports/executive_summary.md"]),
    ("share_late_in_peak_months", pct0, ["README.md", "reports/executive_memo.md", "reports/executive_summary.md"]),
    ("sp_rj_late_rate", pct1, ["README.md", "reports/executive_memo.md", "reports/executive_summary.md",
                               "docs/06_insights_and_evidence.md"]),
    ("sp_rj_distance_matched_expected", pct2, ["README.md", "reports/executive_memo.md",
                                               "reports/executive_summary.md", "docs/06_insights_and_evidence.md"]),
    ("scenario_baseline_late_rate", pct1, ["README.md", "reports/executive_memo.md", "reports/executive_summary.md"]),
    ("scenario_base_new_late_rate", pct1, ["README.md", "reports/executive_memo.md", "reports/executive_summary.md"]),
    ("scenario_low_new_late_rate", pct1, ["README.md", "reports/executive_memo.md", "reports/executive_summary.md"]),
    ("scenario_high_new_late_rate", pct1, ["README.md", "reports/executive_memo.md", "reports/executive_summary.md"]),
    ("scenario_nov_only_base_new_late_rate", pct1, ["README.md", "reports/executive_memo.md",
                                                    "reports/executive_summary.md"]),
    ("backtest_current_late_rate", pct2, ["README.md", "reports/executive_memo.md", "reports/executive_summary.md"]),
    ("backtest_matched_late_rate", pct2, ["README.md", "reports/executive_memo.md", "reports/executive_summary.md"]),
    ("share_customers_one_order", pct0, ["README.md", "reports/executive_memo.md"]),
]


@pytest.mark.skipif(KM is None, reason="run the pipeline first")
@pytest.mark.parametrize("key,fmt,docs", CLAIMS, ids=[c[0] for c in CLAIMS])
def test_headline_number_quoted_correctly(key, fmt, docs):
    expected = fmt(KM[key])
    for d in docs:
        assert expected in DOCS[d], f"{d} should quote {key} as {expected}"


@pytest.mark.skipif(KM is None, reason="run the pipeline first")
def test_ratio_and_review_gaps_quoted():
    ratio = f"{KM['sp_rj_ratio_to_expected']:.1f}×"
    for d in ("README.md", "reports/executive_summary.md", "docs/06_insights_and_evidence.md"):
        assert ratio in DOCS[d], d
    for k in ("review_gap_raw_pp", "review_gap_within_seller_pp", "review_gap_logit_ame_pp"):
        assert f"{KM[k]:.1f} pp" in DOCS["docs/06_insights_and_evidence.md"], k
    lo, hi = KM["review_gap_logit_ci95_pp"]
    assert f"{lo:.1f}–{hi:.1f}" in DOCS["docs/06_insights_and_evidence.md"]
