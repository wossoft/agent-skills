#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from datetime import date, timedelta
from pathlib import Path


SCRIPT = Path(__file__).with_name("build_evidence.py")
SPEC = importlib.util.spec_from_file_location("build_evidence", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def prices(end: date, count: int, start: float = 100.0, step: float = 0.2) -> list[dict[str, object]]:
    return [
        {"date": (end - timedelta(days=count - index - 1)).isoformat(), "close": start + index * step}
        for index in range(count)
    ]


class BuildEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.today = date(2026, 6, 29)
        self.policy = {
            "version": "v1",
            "max_single_position": 0.2,
            "max_industry_exposure": 0.35,
            "min_cash_weight": 0.1,
            "max_portfolio_drawdown": 0.15,
            "minimum_rebalance_interval_days": 5,
        }

    def test_portfolio_flags_policy_breach_and_builds_trend(self) -> None:
        snapshot = {
            "snapshot_id": "p1",
            "as_of_date": self.today.isoformat(),
            "scope": {"type": "portfolio", "name": "real"},
            "risk_policy": self.policy,
            "portfolio": {
                "cash_weight": 0.05,
                "holdings": [
                    {
                        "symbol": "510300",
                        "industry": "宽基",
                        "weight": 0.3,
                        "market_price": 124.0,
                        "cost_price": 100.0,
                        "prices": prices(self.today, 121),
                    }
                ],
            },
            "sources": [],
        }

        result = MODULE.build_evidence(snapshot, "portfolio-review", self.today, 7)

        violation_types = {item["type"] for item in result["portfolio_evidence"]["policy_violations"]}
        self.assertEqual({"single-position", "minimum-cash"}, violation_types)
        self.assertEqual("bullish", result["technical_evidence"][0]["technical_state"])
        self.assertTrue(result["readiness"]["position_sizing_ready"])

    def test_research_without_sources_blocks_position_signal(self) -> None:
        snapshot = {
            "snapshot_id": "r1",
            "as_of_date": self.today.isoformat(),
            "scope": {"type": "instrument", "name": "candidate"},
            "risk_policy": self.policy,
            "targets": [{"symbol": "600519", "prices": prices(self.today, 121)}],
            "sources": [],
        }

        result = MODULE.build_evidence(snapshot, "research", self.today, 7)

        self.assertTrue(result["readiness"]["quantitative_evidence_ready"])
        self.assertFalse(result["readiness"]["position_signal_ready"])
        self.assertFalse(result["readiness"]["position_sizing_ready"])

    def test_missing_risk_policy_allows_signal_but_not_sizing(self) -> None:
        snapshot = {
            "snapshot_id": "r2",
            "as_of_date": self.today.isoformat(),
            "scope": {"type": "instrument", "name": "candidate"},
            "targets": [{"symbol": "510300", "prices": prices(self.today, 121)}],
            "sources": [
                {
                    "id": "s1",
                    "title": "official source",
                    "provider": "AKShare",
                    "function": "stock_zh_a_hist",
                    "retrieved_date": self.today.isoformat(),
                }
            ],
        }

        result = MODULE.build_evidence(snapshot, "research", self.today, 7)

        self.assertTrue(result["readiness"]["position_signal_ready"])
        self.assertFalse(result["readiness"]["position_sizing_ready"])
        self.assertIn("missing risk_policy", result["data_gaps"])


if __name__ == "__main__":
    unittest.main()
