"""Run the full, reproducible pipeline end to end.

    python -m olist_ba.pipeline            # everything (downloads data if missing)
    python -m olist_ba.pipeline --skip-download

Steps: ingest -> SQL build/validate/analyse (DuckDB) -> pandas clean -> stats -> root cause
-> scenarios -> charts -> BI export -> Power Query generation -> T-SQL transpile -> key metrics.
"""
from __future__ import annotations

import argparse
import json
import time

import pandas as pd

from . import (charts, clean, export_bi, ingest, powerbi_assets, root_cause, run_sql, scenarios, stats,
               transpile_tsql)
from .config import OUTPUTS


def key_metrics() -> dict:
    """Single source of truth for every headline number quoted in README/docs/reports."""
    q = lambda n: pd.read_csv(OUTPUTS / "sql" / "analysis" / f"{n}.csv")  # noqa: E731
    k = q("q01_kpi_scorecard").iloc[0]
    st = json.loads((OUTPUTS / "stats" / "stats_summary.json").read_text())
    rc = json.loads((OUTPUTS / "root_cause" / "root_cause_summary.json").read_text())
    dec = pd.read_csv(OUTPUTS / "root_cause" / "late_decomposition.csv").set_index("origin")
    bt = pd.read_csv(OUTPUTS / "root_cause" / "estimate_backtest.csv")
    sc = pd.read_csv(OUTPUTS / "scenarios" / "scenario_results.csv")
    comb = sc[sc["lever"].str.startswith("Combined")].set_index("case")
    nov = pd.read_csv(OUTPUTS / "scenarios" / "scenario_variant_november_only.csv").set_index("case")
    sla = q("q09_seller_shipping_sla").set_index("seller_handoff")
    yoy = q("q03_yoy_same_period").set_index("month_num")
    m = bt[bt["is_matched_to_current_avg_promise"]].iloc[0]
    dm = pd.read_csv(OUTPUTS / "root_cause" / "lane_distance_matched.csv").set_index("route")
    km = {
        "revenue_orders": int(k["revenue_orders"]),
        "product_revenue": float(k["product_revenue"]),
        "unique_customers": int(k["unique_customers"]),
        "late_rate": round(1 - float(k["on_time_delivery_rate"]), 4),
        "avg_delivery_days": float(k["avg_delivery_days"]),
        "low_review_rate": float(k["low_review_rate"]),
        "avg_review_delivered": float(k["avg_review_score_delivered"]),
        "yoy_jan_aug_revenue_growth_pct": float(yoy.loc[99, "revenue_yoy_pct"]),
        "yoy_aug_revenue_growth_pct": float(yoy.loc[8, "revenue_yoy_pct"]),
        "late_orders_single_seller": int(dec.loc["Total", "Total"]),
        "share_late_post_handoff": float(dec.loc["Seller on time -> delay after carrier handoff", "Total (share)"]),
        "share_late_seller_sla_miss": float(dec.loc["Seller missed shipping limit", "Total (share)"]),
        "share_late_in_peak_months": float(dec.loc["Total", "Peak months (Nov-17, Feb-18, Mar-18) (share)"]),
        "seller_sla_miss_share_of_delivered": round(float(sla.loc["Seller missed shipping limit", "share_pct"]) / 100, 4),
        "late_rate_sla_miss": float(sla.loc["Seller missed shipping limit", "late_delivery_rate"]),
        "late_rate_within_sla": float(sla.loc["Seller shipped within limit", "late_delivery_rate"]),
        "top15_lanes_share_of_excess_late": rc["route_concentration"]["top15_share_of_positive_excess"],
        "top15_lanes_share_of_volume": rc["route_concentration"]["top15_share_of_delivered"],
        "sp_rj_late_rate": rc["route_concentration"]["sp_to_rj_late_rate"],
        "sp_sp_late_rate": rc["route_concentration"]["sp_to_sp_late_rate"],
        "sp_rj_orders": rc["route_concentration"]["sp_to_rj_delivered"],
        "rj_revenue_share": st["rj_vs_sp"]["RJ_revenue_share"],
        "sp_rj_distance_matched_expected": float(dm.loc["SP->RJ", "distance_matched_expected"]),
        "sp_rj_ratio_to_expected": float(dm.loc["SP->RJ", "ratio_actual_to_expected"]),
        "sp_mg_late_rate": float(dm.loc["SP->MG", "actual_late_rate"]),
        "sp_mg_distance_matched_expected": float(dm.loc["SP->MG", "distance_matched_expected"]),
        "low_review_late": rc["controlled_review_effect"]["raw_low_review_rate_late"],
        "low_review_on_time": rc["controlled_review_effect"]["raw_low_review_rate_on_time"],
        "review_gap_raw_pp": rc["controlled_review_effect"]["raw_gap_pp"],
        "review_gap_within_seller_pp": rc["controlled_review_effect"]["within_seller_gap_pp"],
        "review_gap_logit_ame_pp": rc["controlled_review_effect"]["logit_avg_marginal_effect_pp"],
        "review_gap_logit_ci95_pp": rc["controlled_review_effect"]["logit_ame_ci95_pp"],
        "logit_odds_ratio": rc["controlled_review_effect"]["logit_odds_ratio_late"],
        "repeat_rate_first_late": st["late_first_order_vs_repeat"]["repeat_rate_first_late"],
        "repeat_rate_first_on_time": st["late_first_order_vs_repeat"]["repeat_rate_first_on_time"],
        "repeat_p_value": st["late_first_order_vs_repeat"]["p_value"],
        "spearman_distance_days": st["distance_vs_delivery"]["spearman_distance_delivery_days"],
        "share_customers_one_order": round(float(q("q12_customer_frequency").set_index("frequency_band").loc["1 order", "customer_share_pct"]) / 100, 4),
        "backtest_current_late_rate": float(bt.iloc[0]["late_rate"]),
        "backtest_current_avg_promise": float(bt.iloc[0]["avg_promised_days"]),
        "backtest_matched_policy": m["policy"],
        "backtest_matched_late_rate": float(m["late_rate"]),
        "backtest_matched_avg_promise": float(m["avg_promised_days"]),
        "scenario_baseline_late_rate": float(comb.loc["base", "baseline_late_rate"]),
        "scenario_base_new_late_rate": float(comb.loc["base", "new_late_rate"]),
        "scenario_low_new_late_rate": float(comb.loc["low", "new_late_rate"]),
        "scenario_high_new_late_rate": float(comb.loc["high", "new_late_rate"]),
        "scenario_base_late_orders_avoided": int(comb.loc["base", "late_orders_avoided"]),
        "scenario_base_low_reviews_avoided": int(comb.loc["base", "low_reviews_avoided"]),
        "scenario_baseline_low_review_rate": float(comb.loc["base", "baseline_low_review_rate"]),
        "scenario_base_new_low_review_rate": float(comb.loc["base", "new_low_review_rate"]),
        "scenario_nov_only_base_new_late_rate": float(nov.loc["base", "new_late_rate"]),
        "scenario_nov_only_low_new_late_rate": float(nov.loc["low", "new_late_rate"]),
        "scenario_nov_only_high_new_late_rate": float(nov.loc["high", "new_late_rate"]),
        "lane_persistence_spearman": rc["lane_persistence"]["spearman_lane_late_rate_2017_vs_2018"],
        "sp_rj_ratio_to_platform_2017": rc["lane_persistence"]["sp_rj_ratio_to_platform_2017"],
        "sp_rj_ratio_to_platform_2018": rc["lane_persistence"]["sp_rj_ratio_to_platform_2018"],
    }
    (OUTPUTS / "key_metrics.json").write_text(json.dumps(km, indent=2))
    return km


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--skip-download", action="store_true")
    a = p.parse_args(argv)
    steps = [
        ("ingest", (lambda: None) if a.skip_download else (lambda: ingest.main([]))),
        ("sql: build + validate + analyse", lambda: run_sql.main([])),
        ("pandas clean", clean.main),
        ("statistics", stats.run),
        ("root cause", root_cause.run),
        ("scenarios", scenarios.run),
        ("charts", charts.main),
        ("BI export", export_bi.main),
        ("Power Query generation", powerbi_assets.main),
        ("T-SQL transpile + parse check", transpile_tsql.main),
        ("key metrics", key_metrics),
    ]
    for name, fn in steps:
        t = time.time()
        print(f"==> {name}")
        fn()
        print(f"    done in {time.time() - t:.1f}s")


if __name__ == "__main__":
    main()
