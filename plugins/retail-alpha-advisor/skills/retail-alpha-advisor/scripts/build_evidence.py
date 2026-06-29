#!/usr/bin/env python3
"""Validate a Retail Alpha snapshot and build deterministic evidence.

This script intentionally does not emit buy/sell advice. It separates facts and
risk-policy gates from the agent's cited investment judgment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any


RISK_FIELDS = (
    "max_single_position",
    "max_industry_exposure",
    "min_cash_weight",
    "max_portfolio_drawdown",
    "minimum_rebalance_interval_days",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=("portfolio-review", "research"))
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--today", type=parse_date, default=date.today())
    parser.add_argument("--max-data-age-days", type=int, default=7)
    return parser.parse_args()


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected date in YYYY-MM-DD format") from exc


def require_date(value: Any, path: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{path} must be a YYYY-MM-DD string")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{path} must be a valid YYYY-MM-DD date") from exc


def require_ratio(value: Any, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path} must be a number from 0 to 1")
    result = float(value)
    if not 0 <= result <= 1:
        raise ValueError(f"{path} must be a number from 0 to 1")
    return result


def optional_positive(value: Any, path: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or float(value) <= 0:
        raise ValueError(f"{path} must be a positive number")
    return float(value)


def canonical_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def load_snapshot(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"input file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"input is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("input JSON must be an object")
    return value


def normalize_prices(raw: Any, path: str) -> list[tuple[date, float]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError(f"{path} must be an array")
    by_date: dict[date, float] = {}
    for index, row in enumerate(raw):
        if not isinstance(row, dict):
            raise ValueError(f"{path}[{index}] must be an object")
        trade_date = require_date(row.get("date"), f"{path}[{index}].date")
        close = optional_positive(row.get("close"), f"{path}[{index}].close")
        assert close is not None
        by_date[trade_date] = close
    return sorted(by_date.items())


def trailing_return(closes: list[float], periods: int) -> float | None:
    if len(closes) <= periods:
        return None
    return closes[-1] / closes[-periods - 1] - 1


def moving_average(closes: list[float], periods: int) -> float | None:
    if len(closes) < periods:
        return None
    return statistics.fmean(closes[-periods:])


def annualized_volatility(closes: list[float], periods: int = 60) -> float | None:
    if len(closes) < 3:
        return None
    selected = closes[-(periods + 1) :]
    returns = [math.log(current / previous) for previous, current in zip(selected, selected[1:])]
    if len(returns) < 2:
        return None
    return statistics.stdev(returns) * math.sqrt(252)


def max_drawdown(closes: list[float]) -> float | None:
    if not closes:
        return None
    peak = closes[0]
    worst = 0.0
    for close in closes:
        peak = max(peak, close)
        worst = min(worst, close / peak - 1)
    return worst


def rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 6)


def technical_evidence(item: dict[str, Any], path: str, gaps: list[str]) -> dict[str, Any]:
    symbol = str(item.get("symbol") or "").strip()
    if not symbol:
        raise ValueError(f"{path}.symbol is required")
    prices = normalize_prices(item.get("prices"), f"{path}.prices")
    if not prices:
        gaps.append(f"{symbol}: missing price history")
        return {"symbol": symbol, "observations": 0, "technical_state": "unavailable"}

    closes = [close for _, close in prices]
    latest_date, latest_close = prices[-1]
    sma20 = moving_average(closes, 20)
    sma60 = moving_average(closes, 60)
    sma120 = moving_average(closes, 120)
    return60 = trailing_return(closes, 60)
    if len(closes) < 61:
        gaps.append(f"{symbol}: fewer than 61 closes; basic 60-day trend is unavailable")
        state = "insufficient-history"
    elif sma20 is not None and sma60 is not None and latest_close >= sma20 >= sma60 and return60 is not None and return60 > 0:
        state = "bullish"
    elif sma20 is not None and sma60 is not None and latest_close < sma20 < sma60 and return60 is not None and return60 < 0:
        state = "bearish"
    else:
        state = "mixed"
    if len(closes) < 121:
        gaps.append(f"{symbol}: fewer than 121 closes; full 120-day evidence is unavailable")

    result: dict[str, Any] = {
        "symbol": symbol,
        "latest_price_date": latest_date.isoformat(),
        "latest_close": latest_close,
        "observations": len(closes),
        "return_20d": rounded(trailing_return(closes, 20)),
        "return_60d": rounded(return60),
        "return_120d": rounded(trailing_return(closes, 120)),
        "sma_20": rounded(sma20),
        "sma_60": rounded(sma60),
        "sma_120": rounded(sma120),
        "annualized_volatility_60d": rounded(annualized_volatility(closes)),
        "max_drawdown_available_history": rounded(max_drawdown(closes)),
        "technical_state": state,
    }
    if sma20:
        result["distance_to_sma20"] = rounded(latest_close / sma20 - 1)
    if sma60:
        result["distance_to_sma60"] = rounded(latest_close / sma60 - 1)
    return result


def validate_risk_policy(snapshot: dict[str, Any], gaps: list[str]) -> tuple[dict[str, Any], bool]:
    raw = snapshot.get("risk_policy")
    if not isinstance(raw, dict):
        gaps.append("missing risk_policy")
        return {}, False
    policy: dict[str, Any] = {"version": raw.get("version")}
    missing = [field for field in RISK_FIELDS if raw.get(field) is None]
    for field in missing:
        gaps.append(f"risk_policy.{field} is missing")
    for field in RISK_FIELDS[:-1]:
        if raw.get(field) is not None:
            policy[field] = require_ratio(raw[field], f"risk_policy.{field}")
    interval = raw.get("minimum_rebalance_interval_days")
    if interval is not None:
        if isinstance(interval, bool) or not isinstance(interval, int) or interval < 0:
            raise ValueError("risk_policy.minimum_rebalance_interval_days must be a non-negative integer")
        policy["minimum_rebalance_interval_days"] = interval
    return policy, not missing


def source_evidence(snapshot: dict[str, Any], gaps: list[str]) -> tuple[list[dict[str, Any]], int]:
    raw = snapshot.get("sources", [])
    if not isinstance(raw, list):
        raise ValueError("sources must be an array")
    sources: list[dict[str, Any]] = []
    valid_count = 0
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"sources[{index}] must be an object")
        missing = [field for field in ("id", "title", "provider", "retrieved_date") if not item.get(field)]
        if not item.get("command") and not item.get("function"):
            missing.append("command")
        if missing:
            gaps.append(f"sources[{index}] missing: {', '.join(missing)}")
        else:
            valid_count += 1
        sources.append(
            {
                key: item.get(key)
                for key in (
                    "id",
                    "title",
                    "provider",
                    "provider_version",
                    "command",
                    "function",
                    "upstream",
                    "parameters",
                    "data_date",
                    "retrieved_date",
                    "url",
                )
            }
        )
    return sources, valid_count


def build_portfolio_evidence(
    snapshot: dict[str, Any], policy: dict[str, Any], gaps: list[str]
) -> tuple[dict[str, Any], list[dict[str, Any]], bool]:
    raw = snapshot.get("portfolio")
    if not isinstance(raw, dict):
        gaps.append("missing portfolio")
        return {}, [], False
    holdings = raw.get("holdings")
    if not isinstance(holdings, list) or not holdings:
        gaps.append("portfolio.holdings is missing or empty")
        holdings = []
    cash_raw = raw.get("cash_weight")
    if cash_raw is None:
        gaps.append("portfolio.cash_weight is missing")
        cash_weight = None
    else:
        cash_weight = require_ratio(cash_raw, "portfolio.cash_weight")

    industry_weights: defaultdict[str, float] = defaultdict(float)
    position_rows: list[dict[str, Any]] = []
    technical_rows: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []
    total_position_weight = 0.0
    for index, item in enumerate(holdings):
        if not isinstance(item, dict):
            raise ValueError(f"portfolio.holdings[{index}] must be an object")
        path = f"portfolio.holdings[{index}]"
        symbol = str(item.get("symbol") or "").strip()
        if not symbol:
            raise ValueError(f"{path}.symbol is required")
        weight = require_ratio(item.get("weight"), f"{path}.weight")
        industry = str(item.get("industry") or "").strip()
        if not industry:
            industry = "unknown"
            gaps.append(f"{symbol}: industry is missing")
        market_price = optional_positive(item.get("market_price"), f"{path}.market_price")
        cost_price = optional_positive(item.get("cost_price"), f"{path}.cost_price")
        total_position_weight += weight
        industry_weights[industry] += weight
        row: dict[str, Any] = {
            "symbol": symbol,
            "name": item.get("name"),
            "industry": industry,
            "weight": weight,
            "market_price": market_price,
            "cost_price": cost_price,
            "last_rebalanced_date": item.get("last_rebalanced_date"),
        }
        if market_price is not None and cost_price is not None:
            row["unrealized_return"] = rounded(market_price / cost_price - 1)
        position_rows.append(row)
        technical_rows.append(technical_evidence(item, path, gaps))
        limit = policy.get("max_single_position")
        if limit is not None and weight > limit:
            violations.append({"type": "single-position", "symbol": symbol, "actual": weight, "limit": limit})

    industry_limit = policy.get("max_industry_exposure")
    if industry_limit is not None:
        for industry, weight in industry_weights.items():
            if industry != "unknown" and weight > industry_limit:
                violations.append({"type": "industry-exposure", "industry": industry, "actual": weight, "limit": industry_limit})
    min_cash = policy.get("min_cash_weight")
    if cash_weight is not None and min_cash is not None and cash_weight < min_cash:
        violations.append({"type": "minimum-cash", "actual": cash_weight, "limit": min_cash})
    if cash_weight is not None and total_position_weight + cash_weight > 1.01:
        violations.append({"type": "weight-total", "actual": rounded(total_position_weight + cash_weight), "limit": 1.0})

    hhi = sum(row["weight"] ** 2 for row in position_rows)
    portfolio = {
        "cash_weight": cash_weight,
        "position_weight": rounded(total_position_weight),
        "position_count": len(position_rows),
        "concentration_hhi": rounded(hhi),
        "industry_exposure": dict(sorted((key, rounded(value)) for key, value in industry_weights.items())),
        "positions": position_rows,
        "policy_violations": violations,
    }
    quantitative_ready = bool(position_rows) and all(row.get("observations", 0) >= 61 for row in technical_rows)
    return portfolio, technical_rows, quantitative_ready


def build_research_evidence(snapshot: dict[str, Any], gaps: list[str]) -> tuple[list[dict[str, Any]], bool, bool]:
    scope = snapshot.get("scope")
    scope_type = scope.get("type") if isinstance(scope, dict) else None
    if scope_type not in ("instrument", "industry"):
        gaps.append("scope.type must be instrument or industry for research mode")
    targets = snapshot.get("targets")
    if not isinstance(targets, list) or not targets:
        gaps.append("targets is missing; industry analysis cannot produce a tradable position signal")
        return [], False, scope_type == "industry"
    rows = []
    for index, item in enumerate(targets):
        if not isinstance(item, dict):
            raise ValueError(f"targets[{index}] must be an object")
        technical = technical_evidence(item, f"targets[{index}]", gaps)
        technical.update(
            {
                "name": item.get("name"),
                "instrument_type": item.get("instrument_type"),
                "industry": item.get("industry"),
                "fundamentals": item.get("fundamentals"),
            }
        )
        rows.append(technical)
    quantitative_ready = all(row.get("observations", 0) >= 61 for row in rows)
    return rows, quantitative_ready, scope_type == "industry"


def build_evidence(snapshot: dict[str, Any], mode: str, today: date, max_age_days: int) -> dict[str, Any]:
    snapshot_id = str(snapshot.get("snapshot_id") or "").strip()
    if not snapshot_id:
        raise ValueError("snapshot_id is required")
    as_of = require_date(snapshot.get("as_of_date"), "as_of_date")
    if as_of > today:
        raise ValueError("as_of_date cannot be in the future")
    age_days = (today - as_of).days
    gaps: list[str] = []
    if age_days > max_age_days:
        gaps.append(f"snapshot is stale: {age_days} days old (limit {max_age_days})")

    policy, risk_ready = validate_risk_policy(snapshot, gaps)
    sources, valid_source_count = source_evidence(snapshot, gaps)
    result: dict[str, Any] = {
        "evidence_schema_version": 1,
        "skill": "retail-alpha-advisor",
        "snapshot_id": snapshot_id,
        "mode": mode,
        "data_as_of": as_of.isoformat(),
        "evaluated_on": today.isoformat(),
        "data_age_days": age_days,
        "input_sha256": canonical_hash(snapshot),
        "scope": snapshot.get("scope"),
        "risk_policy": policy,
        "sources": sources,
    }

    if mode == "portfolio-review":
        portfolio, technical, quantitative_ready = build_portfolio_evidence(snapshot, policy, gaps)
        result["portfolio_evidence"] = portfolio
        result["technical_evidence"] = technical
        has_tradable_target = bool(portfolio.get("positions"))
        industry_only = False
    else:
        research, quantitative_ready, industry_only = build_research_evidence(snapshot, gaps)
        result["research_evidence"] = research
        result["industry_evidence"] = snapshot.get("industry_evidence")
        has_tradable_target = bool(research)

    source_ready = valid_source_count > 0
    fresh = age_days <= max_age_days
    result["readiness"] = {
        "fresh_data": fresh,
        "risk_policy_ready": risk_ready,
        "quantitative_evidence_ready": quantitative_ready,
        "external_evidence_present": source_ready,
        "tradable_target_present": has_tradable_target,
        "industry_only": industry_only,
        "position_signal_ready": fresh and quantitative_ready and has_tradable_target and (mode == "portfolio-review" or source_ready),
        "position_sizing_ready": fresh and quantitative_ready and has_tradable_target and risk_ready and (mode == "portfolio-review" or source_ready),
    }
    result["data_gaps"] = list(dict.fromkeys(gaps))
    return result


def main() -> int:
    args = parse_args()
    if args.max_data_age_days < 0:
        raise SystemExit("--max-data-age-days must be non-negative")
    try:
        snapshot = load_snapshot(args.input)
        evidence = build_evidence(snapshot, args.mode, args.today, args.max_data_age_days)
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc
    output = json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
