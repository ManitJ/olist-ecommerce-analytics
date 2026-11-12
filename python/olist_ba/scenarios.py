"""Scenario analysis: potential impact of the proposed operational interventions.

THIS IS A SCENARIO MODEL, NOT A FORECAST. Every number it produces depends on the
assumptions in ASSUMPTIONS below, which are deliberately explicit and adjustable.

Baseline: delivered, single-seller orders purchased in the last 12 months of the window
(Sep 2017 - Aug 2018), i.e. one observed year of operations.

How it avoids double counting
-----------------------------
Interventions overlap (a late SP->RJ order in March with a seller SLA miss is touched by
three levers). For each late order we compute the probability that each lever would have
prevented it, then combine: P(prevented) = 1 - prod(1 - p_i). Expected late orders avoided =
sum of P(prevented) over late orders.

Per-lever prevention probability for a late order = (reduction assumption) x (attributable share),
where the attributable share is the part of that segment's late rate that is ABOVE its
benchmark, e.g. for SP->RJ: (14.3% - 6.9%) / 14.3%. Only the excess is treated as addressable.

Translation to satisfaction: low (1-2 star) reviews avoided = late orders avoided x review gap.
The review gap comes from root_cause.controlled_review_effect (low / base / high =
regression marginal effect / within-seller gap / raw gap). Using it assumes the association
is causal - which this data cannot prove - so the satisfaction figures are upper-bound style
estimates to be validated by a controlled pilot.

Lever L3 (route-calibrated promises) changes the promise, not the physical delivery, so it is
reported separately and NOT added to the operational total.

Usage: python -m olist_ba.scenarios
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .config import OUTPUTS
from .root_cause import OUT as RC_OUT
from .root_cause import PEAK_MONTHS, delivered_with_seller

OUT = OUTPUTS / "scenarios"

ASSUMPTIONS = {
    # Share of the *excess* late orders each lever removes (low / base / high).
    "L1_lane_recovery_excess_reduction": {"low": 0.25, "base": 0.50, "high": 0.75},
    "L2_seller_sla_conversion": {"low": 0.25, "base": 0.50, "high": 0.75},
    "L4_peak_excess_reduction": {"low": 0.25, "base": 0.40, "high": 0.60},
    # Number of worst lanes (by excess late orders, >= 30 deliveries) targeted by L1.
    "L1_target_lanes": 15,
}


def _baseline(d: pd.DataFrame) -> pd.DataFrame:
    return d[(d["purchase_ts"] >= "2017-09-01") & (d["purchase_ts"] < "2018-09-01")].copy()


def attributable_shares(d: pd.DataFrame, n_lanes: int, peak_months=PEAK_MONTHS) -> tuple[pd.DataFrame, dict]:
    """Per-order attributable share of lateness for each lever (computed on the baseline year)."""
    base_rate = d["is_late"].mean()
    # L1: lanes with the most excess late orders
    r = d.groupby("route").agg(n=("order_id", "size"), late=("is_late", "mean"))
    r = r[r["n"] >= 30]
    r["excess"] = (r["late"] - base_rate) * r["n"]
    lanes = r.sort_values("excess", ascending=False).head(n_lanes)
    lane_share = ((lanes["late"] - base_rate) / lanes["late"]).clip(lower=0)
    # L2: seller SLA miss vs within-SLA late rate
    miss_rate = d.loc[d["seller_shipped_late"] == 1, "is_late"].mean()
    ok_rate = d.loc[d["seller_shipped_late"] == 0, "is_late"].mean()
    sla_share = max(0.0, (miss_rate - ok_rate) / miss_rate)
    # L4: peak months vs the rest
    peak = d["purchase_month"].isin(peak_months)
    peak_rate, off_rate = d.loc[peak, "is_late"].mean(), d.loc[~peak, "is_late"].mean()
    peak_share = max(0.0, (peak_rate - off_rate) / peak_rate)

    a = pd.DataFrame(index=d.index)
    a["L1"] = d["route"].map(lane_share).fillna(0.0)
    a["L2"] = np.where(d["seller_shipped_late"] == 1, sla_share, 0.0)
    a["L4"] = np.where(peak, peak_share, 0.0)
    meta = {
        "baseline_late_rate": round(float(base_rate), 4),
        "L1_lanes": lanes.index.tolist(),
        "L1_lane_late_rates": lanes["late"].round(4).to_dict(),
        "L2_late_rate_sla_miss": round(float(miss_rate), 4),
        "L2_late_rate_within_sla": round(float(ok_rate), 4),
        "L2_attributable_share": round(float(sla_share), 4),
        "L4_peak_late_rate": round(float(peak_rate), 4),
        "L4_offpeak_late_rate": round(float(off_rate), 4),
        "L4_attributable_share": round(float(peak_share), 4),
    }
    return a, meta


def run_scenarios(d: pd.DataFrame, review_gap: dict[str, float], assumptions: dict = ASSUMPTIONS) -> tuple[pd.DataFrame, dict]:
    b = _baseline(d)
    shares, meta = attributable_shares(b, assumptions["L1_target_lanes"])
    late = b["is_late"] == 1
    n, n_late = len(b), int(late.sum())
    levers = {"L1": "L1_lane_recovery_excess_reduction", "L2": "L2_seller_sla_conversion",
              "L4": "L4_peak_excess_reduction"}
    rows = []
    for case in ("low", "base", "high"):
        p = {k: shares[k] * assumptions[v][case] for k, v in levers.items()}
        for k in levers:
            avoided = float(p[k][late].sum())
            rows.append({"case": case, "lever": k, "late_orders_avoided": avoided})
        combined = 1 - np.prod([1 - p[k][late] for k in levers], axis=0)
        avoided = float(combined.sum())
        rows.append({"case": case, "lever": "Combined (L1+L2+L4, overlap removed)", "late_orders_avoided": avoided})
    out = pd.DataFrame(rows)
    out["baseline_orders"] = n
    out["baseline_late_orders"] = n_late
    out["baseline_late_rate"] = round(n_late / n, 4)
    out["new_late_rate"] = ((n_late - out["late_orders_avoided"]) / n).round(4)
    out["late_rate_change_pp"] = ((out["new_late_rate"] - out["baseline_late_rate"]) * 100).round(2)
    reviewed = int(b["low_review"].notna().sum())
    late_review_coverage = float(b.loc[late, "low_review"].notna().mean())  # share of late orders with a review
    base_low = float(b["low_review"].sum())
    out["low_reviews_avoided"] = out.apply(
        lambda r: r["late_orders_avoided"] * late_review_coverage * review_gap[r["case"]], axis=1)
    out["baseline_low_review_rate"] = round(base_low / reviewed, 4)
    out["new_low_review_rate"] = ((base_low - out["low_reviews_avoided"]) / reviewed).round(4)
    out["late_orders_avoided"] = out["late_orders_avoided"].round(0).astype(int)
    out["low_reviews_avoided"] = out["low_reviews_avoided"].round(0).astype(int)
    meta.update({"review_gap_used": review_gap, "assumptions": assumptions,
                 "baseline_window": "2017-09-01 to 2018-08-31, delivered single-seller orders"})
    return out, meta


def sensitivity(d: pd.DataFrame, review_gap_base: float) -> pd.DataFrame:
    """Combined late-rate outcome as all three reduction assumptions move together 0%..100%."""
    b = _baseline(d)
    shares, _ = attributable_shares(b, ASSUMPTIONS["L1_target_lanes"])
    late = b["is_late"] == 1
    cov = float(b.loc[late, "low_review"].notna().mean())
    rows = []
    for r in np.linspace(0, 1, 11):
        combined = 1 - np.prod([1 - shares[k][late] * r for k in ("L1", "L2", "L4")], axis=0)
        av = combined.sum()
        rows.append({"reduction_assumption": round(float(r), 2), "late_orders_avoided": int(round(av)),
                     "new_late_rate": round(float((late.sum() - av) / len(b)), 4),
                     "low_reviews_avoided_base_gap": int(round(av * cov * review_gap_base))})
    return pd.DataFrame(rows)


def run() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    rc = json.loads((RC_OUT / "root_cause_summary.json").read_text())["controlled_review_effect"]
    gap = {"low": rc["logit_avg_marginal_effect_pp"] / 100, "base": rc["within_seller_gap_pp"] / 100,
           "high": rc["raw_gap_pp"] / 100}
    d = delivered_with_seller()
    table, meta = run_scenarios(d, gap)
    sens = sensitivity(d, gap["base"])
    bt = pd.read_csv(RC_OUT / "estimate_backtest.csv")
    table.to_csv(OUT / "scenario_results.csv", index=False)
    # Robustness: the 3 peak months were identified ex post. Only November (Black Friday) is
    # predictable, so re-run with L4 acting on November only.
    b = _baseline(d)
    s_nov, m_nov = attributable_shares(b, ASSUMPTIONS["L1_target_lanes"], peak_months=[pd.Timestamp("2017-11-01")])
    late = b["is_late"] == 1
    rows = []
    for case in ("low", "base", "high"):
        r = {k: ASSUMPTIONS[v][case] for k, v in {"L1": "L1_lane_recovery_excess_reduction",
             "L2": "L2_seller_sla_conversion", "L4": "L4_peak_excess_reduction"}.items()}
        p = 1 - np.prod([1 - s_nov[k][late] * r[k] for k in ("L1", "L2", "L4")], axis=0)
        av = float(p.sum())
        rows.append({"case": case, "variant": "L4 = November only", "late_orders_avoided": int(round(av)),
                     "new_late_rate": round((late.sum() - av) / len(b), 4)})
    pd.DataFrame(rows).to_csv(OUT / "scenario_variant_november_only.csv", index=False)
    meta["L4_november_only_attributable_share"] = m_nov["L4_attributable_share"]
    sens.to_csv(OUT / "sensitivity.csv", index=False)
    meta["L3_promise_recalibration_backtest"] = bt.to_dict(orient="records")
    (OUT / "scenario_assumptions_and_meta.json").write_text(json.dumps(meta, indent=2, default=str))
    return {"table": table, "meta": meta, "sensitivity": sens}


if __name__ == "__main__":
    r = run()
    pd.set_option("display.width", 220)
    print(r["table"].to_string(index=False))
    print(r["sensitivity"].to_string(index=False))
    print(json.dumps({k: v for k, v in r["meta"].items() if k != "L3_promise_recalibration_backtest"}, indent=2, default=str))
