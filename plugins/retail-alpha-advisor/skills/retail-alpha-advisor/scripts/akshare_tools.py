#!/usr/bin/env python3
"""Read-only AKShare function tools for Retail Alpha agents."""

from __future__ import annotations

import argparse
import importlib
import json
import math
import re
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime, time, timedelta, timezone
from io import StringIO
from typing import Any, Callable
from zoneinfo import ZoneInfo


class ToolError(RuntimeError):
    pass


_AKSHARE: Any = None
_SYMBOL_PATTERN = re.compile(r"^\d{6}$")
_ETF_PREFIXES = ("15", "16", "50", "51", "52", "53", "56", "58")


def _load_akshare() -> Any:
    global _AKSHARE
    if _AKSHARE is None:
        try:
            _AKSHARE = importlib.import_module("akshare")
        except ModuleNotFoundError as exc:
            raise ToolError(
                "akshare is not installed; run with: uv run --with 'akshare>=1.17,<2.0' python akshare_tools.py ..."
            ) from exc
    return _AKSHARE


def _normalize_symbol(symbol: str) -> str:
    normalized = str(symbol).strip().lower().removeprefix("sh").removeprefix("sz").removeprefix("bj")
    if not _SYMBOL_PATTERN.fullmatch(normalized):
        raise ToolError("symbol must be a six-digit A-share or ETF code")
    return normalized


def _instrument_type(symbol: str, requested: str) -> str:
    if requested not in ("auto", "stock", "etf"):
        raise ToolError("instrument_type must be auto, stock, or etf")
    if requested != "auto":
        return requested
    return "etf" if symbol.startswith(_ETF_PREFIXES) else "stock"


def _market_symbol(symbol: str) -> str:
    if symbol.startswith(("6", "5", "9")):
        return f"sh{symbol}"
    if symbol.startswith(("4", "8")):
        return f"bj{symbol}"
    return f"sz{symbol}"


def _quiet_call(function: Callable[[], Any]) -> Any:
    with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
        return function()


def _has_data(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (dict, list, tuple, str)):
        return bool(value)
    return True


def _run_provider_chain(
    candidates: list[tuple[str, str, Callable[[], Any]]],
) -> tuple[Any, str, str, list[dict[str, Any]], dict[str, str], list[str]]:
    attempts: list[dict[str, Any]] = []
    errors: dict[str, str] = {}
    functions: list[str] = []
    for provider, function, fetch in candidates:
        functions.append(function)
        try:
            data = fetch()
            if not _has_data(data):
                raise ToolError("returned no data")
        except Exception as exc:
            message = str(exc)
            errors[function] = message
            attempts.append({"provider": provider, "function": function, "status": "failed", "error": message})
            continue
        attempts.append({"provider": provider, "function": function, "status": "success"})
        return data, provider, function, attempts, errors, functions
    raise ToolError(f"all providers failed: {json.dumps(attempts, ensure_ascii=False)}")


def _compact_date(value: str | None, default: date) -> str:
    if value is None:
        return default.strftime("%Y%m%d")
    try:
        return datetime.strptime(value, "%Y%m%d").strftime("%Y%m%d")
    except ValueError as exc:
        raise ToolError("dates must use YYYYMMDD") from exc


def _bounded_limit(value: int, maximum: int = 500) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise ToolError(f"limit must be an integer from 1 to {maximum}")
    return value


def _clean(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return None if math.isnan(value) or math.isinf(value) else value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]
    if hasattr(value, "item"):
        try:
            return _clean(value.item())
        except (TypeError, ValueError):
            pass
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except (TypeError, ValueError):
            pass
    text = str(value)
    return None if text.lower() in ("nan", "nat", "none") else text


def _records(frame: Any, limit: int, *, tail: bool = False) -> list[dict[str, Any]]:
    if frame is None or getattr(frame, "empty", False):
        return []
    columns = {str(column).lower() for column in getattr(frame, "columns", [])}
    if not columns.intersection({"date", "日期", "数据日期", "report_date"}) and hasattr(frame, "reset_index"):
        frame = frame.reset_index()
    try:
        raw = frame.to_dict("records")
    except Exception as exc:
        raise ToolError(f"AKShare returned an unsupported table: {exc}") from exc
    selected = raw[-limit:] if tail else raw[:limit]
    return [_clean(row) for row in selected]


def _find_value(row: dict[str, Any], candidates: tuple[str, ...]) -> Any:
    lowered = {str(key).lower(): value for key, value in row.items()}
    for candidate in candidates:
        if candidate in row:
            return row[candidate]
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]
    return None


def _latest_data_date(rows: list[dict[str, Any]]) -> str | None:
    values = []
    for row in rows:
        value = _find_value(
            row,
            ("date", "日期", "数据日期", "report_date", "报告期", "公告日期", "最新价日期"),
        )
        if value is not None:
            values.append(str(value))
    return max(values) if values else None


def _normalize_market_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mapping = {
        "日期": "date",
        "开盘": "open",
        "最高": "high",
        "最低": "low",
        "收盘": "close",
        "成交量": "volume",
        "成交额": "amount",
        "振幅": "amplitude_pct",
        "涨跌幅": "change_pct",
        "涨跌额": "change",
        "换手率": "turnover_pct",
    }
    return [{mapping.get(str(key), str(key)): value for key, value in row.items()} for row in rows]


def _item_value_dict(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        str(_find_value(row, ("item", "项目"))): _find_value(row, ("value", "值"))
        for row in rows
        if _find_value(row, ("item", "项目")) is not None
    }


def _matching_symbol_row(rows: list[dict[str, Any]], symbol: str) -> dict[str, Any]:
    candidates = {symbol.lower(), _market_symbol(symbol).lower()}
    for row in rows:
        value = str(_find_value(row, ("代码", "code", "symbol")) or "").lower()
        if value in candidates or value.zfill(6) == symbol:
            return row
    return {}


def _filter_date_rows(rows: list[dict[str, Any]], start: str, end: str) -> list[dict[str, Any]]:
    selected = []
    for row in rows:
        value = _find_value(row, ("date", "日期"))
        if value is None:
            continue
        compact = str(value)[:10].replace("-", "")
        if start <= compact <= end:
            selected.append(row)
    return selected


def _fallback_quality_flags(attempts: list[dict[str, Any]], selected_provider: str) -> list[str]:
    failed = [item["provider"] for item in attempts if item["status"] == "failed"]
    return [f"used {selected_provider} fallback after failures from: {', '.join(failed)}"] if failed else []


def _china_now() -> datetime:
    return datetime.now(ZoneInfo("Asia/Shanghai"))


def _remove_incomplete_today(rows: list[dict[str, Any]], include_incomplete_today: bool) -> tuple[list[dict[str, Any]], list[str]]:
    if include_incomplete_today:
        return rows, []
    now = _china_now()
    if now.time() >= time(15, 10):
        return rows, []
    today = now.date().isoformat()
    filtered = [row for row in rows if str(row.get("date"))[:10] != today]
    if len(filtered) == len(rows):
        return rows, []
    return filtered, [f"excluded incomplete current-day bar for {today} before market close"]


def _response(
    *,
    tool: str,
    title: str,
    functions: list[str],
    upstream: str,
    parameters: dict[str, Any],
    data: Any,
    latest_data_date: str | None = None,
    component_errors: dict[str, str] | None = None,
    quality_flags: list[str] | None = None,
    attempts: list[dict[str, Any]] | None = None,
    selected_provider: str | None = None,
    selected_function: str | None = None,
) -> dict[str, Any]:
    ak = _load_akshare()
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    scope = str(parameters.get("symbol") or parameters.get("industry") or "market")
    source_id = f"akshare-{tool}-{scope}-{retrieved_at[:10]}"
    result = {
        "ok": True,
        "tool": tool,
        "provider": "AKShare",
        "provider_version": getattr(ak, "__version__", "unknown"),
        "functions": functions,
        "upstream": upstream,
        "selected_provider": selected_provider or upstream,
        "selected_function": selected_function or (functions[-1] if functions else None),
        "retrieved_at": retrieved_at,
        "parameters": parameters,
        "latest_data_date": latest_data_date,
        "data": data,
        "source": {
            "id": source_id,
            "title": title,
            "provider": "AKShare",
            "provider_version": getattr(ak, "__version__", "unknown"),
            "function": selected_function or (functions[-1] if functions else None),
            "upstream": selected_provider or upstream,
            "data_date": latest_data_date,
            "retrieved_date": retrieved_at[:10],
        },
    }
    if component_errors:
        result["component_errors"] = component_errors
    if quality_flags:
        result["quality_flags"] = quality_flags
    if attempts:
        result["attempts"] = attempts
    return result


def get_instrument_profile(symbol: str, instrument_type: str = "auto") -> dict[str, Any]:
    symbol = _normalize_symbol(symbol)
    resolved_type = _instrument_type(symbol, instrument_type)
    ak = _load_akshare()
    if resolved_type == "stock":
        candidates = [
            (
                "EastMoney",
                "stock_individual_info_em",
                lambda: _item_value_dict(_records(ak.stock_individual_info_em(symbol=symbol, timeout=15), 100)),
            ),
            (
                "Xueqiu",
                "stock_individual_basic_info_xq",
                lambda: _item_value_dict(
                    _records(
                        _quiet_call(lambda: ak.stock_individual_basic_info_xq(symbol=_market_symbol(symbol).upper(), timeout=15)),
                        100,
                    )
                ),
            ),
            (
                "CNInfo",
                "stock_profile_cninfo",
                lambda: _records(ak.stock_profile_cninfo(symbol=symbol), 20),
            ),
        ]
    else:
        candidates = [
            (
                "EastMoney",
                "fund_etf_spot_em",
                lambda: _matching_symbol_row(_records(_quiet_call(ak.fund_etf_spot_em), 10000), symbol),
            ),
            (
                "Xueqiu",
                "stock_individual_spot_xq",
                lambda: _item_value_dict(
                    _records(_quiet_call(lambda: ak.stock_individual_spot_xq(symbol=_market_symbol(symbol).upper(), timeout=15)), 100)
                ),
            ),
        ]
    data, selected_provider, selected_function, attempts, errors, functions = _run_provider_chain(candidates)
    return _response(
        tool="get_instrument_profile",
        title=f"{symbol} instrument profile",
        functions=functions,
        upstream=selected_provider,
        parameters={"symbol": symbol, "instrument_type": resolved_type},
        data=data,
        component_errors=errors or None,
        quality_flags=_fallback_quality_flags(attempts, selected_provider),
        attempts=attempts,
        selected_provider=selected_provider,
        selected_function=selected_function,
    )


def get_realtime_quote(symbol: str, instrument_type: str = "auto") -> dict[str, Any]:
    symbol = _normalize_symbol(symbol)
    resolved_type = _instrument_type(symbol, instrument_type)
    ak = _load_akshare()
    if resolved_type == "stock":
        candidates = [
            (
                "EastMoney",
                "stock_bid_ask_em",
                lambda: _item_value_dict(_records(ak.stock_bid_ask_em(symbol=symbol), 100)),
            ),
            (
                "Xueqiu",
                "stock_individual_spot_xq",
                lambda: _item_value_dict(
                    _records(_quiet_call(lambda: ak.stock_individual_spot_xq(symbol=_market_symbol(symbol).upper(), timeout=15)), 100)
                ),
            ),
            (
                "Sina",
                "stock_zh_a_spot",
                lambda: _matching_symbol_row(_records(_quiet_call(ak.stock_zh_a_spot), 10000), symbol),
            ),
        ]
    else:
        candidates = [
            (
                "EastMoney",
                "fund_etf_spot_em",
                lambda: _matching_symbol_row(_records(_quiet_call(ak.fund_etf_spot_em), 10000), symbol),
            ),
            (
                "Xueqiu",
                "stock_individual_spot_xq",
                lambda: _item_value_dict(
                    _records(_quiet_call(lambda: ak.stock_individual_spot_xq(symbol=_market_symbol(symbol).upper(), timeout=15)), 100)
                ),
            ),
        ]
    data, selected_provider, selected_function, attempts, errors, functions = _run_provider_chain(candidates)
    return _response(
        tool="get_realtime_quote",
        title=f"{symbol} real-time quote",
        functions=functions,
        upstream=selected_provider,
        parameters={"symbol": symbol, "instrument_type": resolved_type},
        data=data,
        component_errors=errors or None,
        quality_flags=_fallback_quality_flags(attempts, selected_provider),
        attempts=attempts,
        selected_provider=selected_provider,
        selected_function=selected_function,
    )


def get_company_business(symbol: str, composition_limit: int = 100) -> dict[str, Any]:
    symbol = _normalize_symbol(symbol)
    composition_limit = _bounded_limit(composition_limit, 500)
    ak = _load_akshare()
    candidates = [
        (
            "10jqka",
            "stock_zyjs_ths",
            lambda: _records(ak.stock_zyjs_ths(symbol=symbol), 20),
        ),
        (
            "Xueqiu",
            "stock_individual_basic_info_xq",
            lambda: _item_value_dict(
                _records(
                    _quiet_call(lambda: ak.stock_individual_basic_info_xq(symbol=_market_symbol(symbol).upper(), timeout=15)),
                    100,
                )
            ),
        ),
        (
            "CNInfo",
            "stock_profile_cninfo",
            lambda: _records(ak.stock_profile_cninfo(symbol=symbol), 20),
        ),
    ]
    business, selected_provider, selected_function, business_attempts, errors, functions = _run_provider_chain(candidates)
    composition_function = "stock_zygc_em"
    try:
        composition = _records(
            ak.stock_zygc_em(symbol=_market_symbol(symbol).upper()),
            composition_limit,
        )
        if not composition:
            raise ToolError("returned no data")
        composition_attempt = {
            "provider": "EastMoney",
            "function": composition_function,
            "status": "success",
            "component": "main_business_composition",
        }
    except Exception as exc:
        composition = []
        errors[composition_function] = str(exc)
        composition_attempt = {
            "provider": "EastMoney",
            "function": composition_function,
            "status": "failed",
            "component": "main_business_composition",
            "error": str(exc),
        }
    functions.append(composition_function)
    attempts = [*business_attempts, composition_attempt]
    return _response(
        tool="get_company_business",
        title=f"{symbol} company business information",
        functions=functions,
        upstream=f"{selected_provider}/EastMoney",
        parameters={"symbol": symbol, "composition_limit": composition_limit},
        data={"business_introduction": business, "main_business_composition": composition},
        latest_data_date=_latest_data_date(composition),
        component_errors=errors or None,
        quality_flags=_fallback_quality_flags(business_attempts, selected_provider),
        attempts=attempts,
        selected_provider=selected_provider,
        selected_function=selected_function,
    )


def get_price_history(
    symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
    adjust: str = "qfq",
    period: str = "daily",
    instrument_type: str = "auto",
    limit: int = 500,
    include_incomplete_today: bool = False,
) -> dict[str, Any]:
    symbol = _normalize_symbol(symbol)
    resolved_type = _instrument_type(symbol, instrument_type)
    if adjust not in ("qfq", "hfq", "none"):
        raise ToolError("adjust must be qfq, hfq, or none")
    if period not in ("daily", "weekly", "monthly"):
        raise ToolError("period must be daily, weekly, or monthly")
    limit = _bounded_limit(limit, 2000)
    today = date.today()
    start = _compact_date(start_date, today - timedelta(days=550))
    end = _compact_date(end_date, today)
    if start > end:
        raise ToolError("start_date must be on or before end_date")
    ak = _load_akshare()
    adjust_arg = "" if adjust == "none" else adjust
    if resolved_type == "stock":
        candidates = [
            (
                "EastMoney",
                "stock_zh_a_hist",
                lambda: _normalize_market_rows(
                    _records(
                        ak.stock_zh_a_hist(
                            symbol=symbol,
                            period=period,
                            start_date=start,
                            end_date=end,
                            adjust=adjust_arg,
                            timeout=20,
                        ),
                        limit,
                        tail=True,
                    )
                ),
            )
        ]
        if period == "daily":
            candidates.extend(
                [
                    (
                        "Tencent",
                        "stock_zh_a_hist_tx",
                        lambda: _normalize_market_rows(
                            _records(
                                _quiet_call(
                                    lambda: ak.stock_zh_a_hist_tx(
                                        symbol=_market_symbol(symbol), start_date=start, end_date=end, adjust=adjust_arg
                                    )
                                ),
                                limit,
                                tail=True,
                            )
                        ),
                    ),
                    (
                        "Sina",
                        "stock_zh_a_daily",
                        lambda: _normalize_market_rows(
                            _records(
                                _quiet_call(
                                    lambda: ak.stock_zh_a_daily(
                                        symbol=_market_symbol(symbol), start_date=start, end_date=end, adjust=adjust_arg
                                    )
                                ),
                                limit,
                                tail=True,
                            )
                        ),
                    ),
                ]
            )
    else:
        candidates = [
            (
                "EastMoney",
                "fund_etf_hist_em",
                lambda: _normalize_market_rows(
                    _records(
                        ak.fund_etf_hist_em(
                            symbol=symbol,
                            period=period,
                            start_date=start,
                            end_date=end,
                            adjust=adjust_arg,
                        ),
                        limit,
                        tail=True,
                    )
                ),
            )
        ]
        if period == "daily":
            candidates.append(
                (
                    "Tencent",
                    "stock_zh_a_hist_tx",
                    lambda: _normalize_market_rows(
                        _records(
                            _quiet_call(
                                lambda: ak.stock_zh_a_hist_tx(
                                    symbol=_market_symbol(symbol), start_date=start, end_date=end, adjust=adjust_arg
                                )
                            ),
                            limit,
                            tail=True,
                        )
                    ),
                )
            )
            if adjust == "none":
                candidates.append(
                    (
                        "Sina",
                        "fund_etf_hist_sina",
                        lambda: _normalize_market_rows(
                            _filter_date_rows(
                                _records(_quiet_call(lambda: ak.fund_etf_hist_sina(symbol=_market_symbol(symbol))), 10000),
                                start,
                                end,
                            )[-limit:]
                        ),
                    )
                )
    rows, selected_provider, selected_function, attempts, errors, functions = _run_provider_chain(candidates)
    rows, quality_flags = _remove_incomplete_today(rows, include_incomplete_today)
    if not rows:
        raise ToolError(f"all providers returned no complete price rows for {symbol}")
    quality_flags.extend(_fallback_quality_flags(attempts, selected_provider))
    return _response(
        tool="get_price_history",
        title=f"{symbol} {adjust} {period} price history",
        functions=functions,
        upstream=selected_provider,
        parameters={
            "symbol": symbol,
            "instrument_type": resolved_type,
            "start_date": start,
            "end_date": end,
            "adjust": adjust,
            "period": period,
            "limit": limit,
            "include_incomplete_today": include_incomplete_today,
        },
        data=rows,
        latest_data_date=_latest_data_date(rows),
        component_errors=errors or None,
        quality_flags=quality_flags,
        attempts=attempts,
        selected_provider=selected_provider,
        selected_function=selected_function,
    )


def get_stock_financials(symbol: str, indicator: str = "按报告期", limit: int = 20) -> dict[str, Any]:
    symbol = _normalize_symbol(symbol)
    limit = _bounded_limit(limit, 100)
    ak = _load_akshare()
    candidates = [
        (
            "10jqka",
            "stock_financial_abstract_new_ths",
            lambda: _records(ak.stock_financial_abstract_new_ths(symbol=symbol, indicator=indicator), limit),
        ),
        (
            "Sina",
            "stock_financial_analysis_indicator",
            lambda: _records(ak.stock_financial_analysis_indicator(symbol=symbol, start_year="2015"), limit),
        ),
    ]
    rows, selected_provider, selected_function, attempts, errors, functions = _run_provider_chain(candidates)
    return _response(
        tool="get_stock_financials",
        title=f"{symbol} financial indicators",
        functions=functions,
        upstream=selected_provider,
        parameters={"symbol": symbol, "indicator": indicator, "limit": limit},
        data=rows,
        latest_data_date=_latest_data_date(rows),
        component_errors=errors or None,
        quality_flags=_fallback_quality_flags(attempts, selected_provider),
        attempts=attempts,
        selected_provider=selected_provider,
        selected_function=selected_function,
    )


def get_stock_valuation(symbol: str, limit: int = 120) -> dict[str, Any]:
    symbol = _normalize_symbol(symbol)
    limit = _bounded_limit(limit, 1000)
    ak = _load_akshare()
    rows, selected_provider, selected_function, attempts, errors, functions = _run_provider_chain(
        [("EastMoney", "stock_value_em", lambda: _records(ak.stock_value_em(symbol=symbol), limit, tail=True))]
    )
    return _response(
        tool="get_stock_valuation",
        title=f"{symbol} valuation data",
        functions=functions,
        upstream=selected_provider,
        parameters={"symbol": symbol, "limit": limit},
        data=rows,
        latest_data_date=_latest_data_date(rows),
        component_errors=errors or None,
        attempts=attempts,
        selected_provider=selected_provider,
        selected_function=selected_function,
    )


def get_stock_news(symbol: str, limit: int = 20) -> dict[str, Any]:
    symbol = _normalize_symbol(symbol)
    limit = _bounded_limit(limit, 100)
    ak = _load_akshare()
    rows, selected_provider, selected_function, attempts, errors, functions = _run_provider_chain(
        [("EastMoney", "stock_news_em", lambda: _records(ak.stock_news_em(symbol=symbol), limit))]
    )
    return _response(
        tool="get_stock_news",
        title=f"{symbol} recent news discovery feed",
        functions=functions,
        upstream=selected_provider,
        parameters={"symbol": symbol, "limit": limit},
        data=rows,
        latest_data_date=_latest_data_date(rows),
        component_errors=errors or None,
        attempts=attempts,
        selected_provider=selected_provider,
        selected_function=selected_function,
    )


def list_industries(limit: int = 200) -> dict[str, Any]:
    limit = _bounded_limit(limit, 1000)
    ak = _load_akshare()
    candidates = [
        ("EastMoney", "stock_board_industry_name_em", lambda: _records(ak.stock_board_industry_name_em(), limit)),
        ("10jqka", "stock_board_industry_name_ths", lambda: _records(_quiet_call(ak.stock_board_industry_name_ths), limit)),
    ]
    rows, selected_provider, selected_function, attempts, errors, functions = _run_provider_chain(candidates)
    return _response(
        tool="list_industries",
        title="Industry board list",
        functions=functions,
        upstream=selected_provider,
        parameters={"limit": limit},
        data=rows,
        latest_data_date=_latest_data_date(rows),
        component_errors=errors or None,
        quality_flags=_fallback_quality_flags(attempts, selected_provider),
        attempts=attempts,
        selected_provider=selected_provider,
        selected_function=selected_function,
    )


def get_industry_snapshot(
    industry: str,
    start_date: str | None = None,
    end_date: str | None = None,
    adjust: str = "none",
    constituent_limit: int = 100,
    history_limit: int = 500,
) -> dict[str, Any]:
    industry = str(industry).strip()
    if not industry or len(industry) > 64:
        raise ToolError("industry must be a non-empty name or board code up to 64 characters")
    if adjust not in ("qfq", "hfq", "none"):
        raise ToolError("adjust must be qfq, hfq, or none")
    constituent_limit = _bounded_limit(constituent_limit, 500)
    history_limit = _bounded_limit(history_limit, 2000)
    today = date.today()
    start = _compact_date(start_date, today - timedelta(days=550))
    end = _compact_date(end_date, today)
    if start > end:
        raise ToolError("start_date must be on or before end_date")
    ak = _load_akshare()
    data: dict[str, Any] = {}
    errors: dict[str, str] = {}
    attempts: list[dict[str, Any]] = []
    functions = [
        "stock_board_industry_spot_em",
        "stock_board_industry_hist_em",
        "stock_board_industry_cons_em",
    ]
    calls: list[tuple[str, Callable[[], Any], int]] = [
        (functions[0], lambda: ak.stock_board_industry_spot_em(symbol=industry), 10),
        (
            functions[1],
            lambda: ak.stock_board_industry_hist_em(
                symbol=industry,
                start_date=start,
                end_date=end,
                period="日k",
                adjust="" if adjust == "none" else adjust,
            ),
            history_limit,
        ),
        (functions[2], lambda: ak.stock_board_industry_cons_em(symbol=industry), constituent_limit),
    ]
    for function, call, limit in calls:
        key = {functions[0]: "spot", functions[1]: "history", functions[2]: "constituents"}[function]
        try:
            rows = _records(call(), limit)
            data[key] = _normalize_market_rows(rows) if key == "history" else rows
            if not rows:
                errors[function] = "returned no data"
                attempts.append({"provider": "EastMoney", "function": function, "component": key, "status": "failed", "error": "returned no data"})
            else:
                attempts.append({"provider": "EastMoney", "function": function, "component": key, "status": "success"})
        except Exception as exc:
            data[key] = []
            errors[function] = str(exc)
            attempts.append({"provider": "EastMoney", "function": function, "component": key, "status": "failed", "error": str(exc)})
    if not data.get("spot"):
        fallback = "stock_board_industry_info_ths"
        functions.append(fallback)
        try:
            data["spot"] = _records(_quiet_call(lambda: ak.stock_board_industry_info_ths(symbol=industry)), 20)
            attempts.append({"provider": "10jqka", "function": fallback, "component": "spot", "status": "success"})
        except Exception as exc:
            errors[fallback] = str(exc)
            attempts.append({"provider": "10jqka", "function": fallback, "component": "spot", "status": "failed", "error": str(exc)})
    if not data.get("history"):
        fallback = "stock_board_industry_index_ths"
        functions.append(fallback)
        try:
            rows = _records(
                _quiet_call(lambda: ak.stock_board_industry_index_ths(symbol=industry, start_date=start, end_date=end)),
                history_limit,
                tail=True,
            )
            data["history"] = _normalize_market_rows(rows)
            attempts.append({"provider": "10jqka", "function": fallback, "component": "history", "status": "success"})
        except Exception as exc:
            errors[fallback] = str(exc)
            attempts.append({"provider": "10jqka", "function": fallback, "component": "history", "status": "failed", "error": str(exc)})
    data["history"], quality_flags = _remove_incomplete_today(data.get("history", []), False)
    if not any(data.values()):
        raise ToolError(f"industry endpoints returned no data for {industry}: {errors}")
    return _response(
        tool="get_industry_snapshot",
        title=f"{industry} industry board snapshot",
        functions=functions,
        upstream="EastMoney/10jqka" if any(name.endswith("_ths") for name in functions) else "EastMoney",
        parameters={
            "industry": industry,
            "start_date": start,
            "end_date": end,
            "adjust": adjust,
            "constituent_limit": constituent_limit,
            "history_limit": history_limit,
        },
        data=data,
        latest_data_date=_latest_data_date(data.get("history", [])),
        component_errors=errors or None,
        quality_flags=quality_flags,
        attempts=attempts,
        selected_provider="mixed",
        selected_function="industry-component-bundle",
    )


_FUNCTIONS: dict[str, Callable[..., dict[str, Any]]] = {
    "get_instrument_profile": get_instrument_profile,
    "get_realtime_quote": get_realtime_quote,
    "get_company_business": get_company_business,
    "get_price_history": get_price_history,
    "get_stock_financials": get_stock_financials,
    "get_stock_valuation": get_stock_valuation,
    "get_stock_news": get_stock_news,
    "list_industries": list_industries,
    "get_industry_snapshot": get_industry_snapshot,
}


def get_tool_definitions() -> list[dict[str, Any]]:
    symbol = {"type": "string", "pattern": "^[0-9]{6}$", "description": "Six-digit A-share or ETF code"}
    instrument_type = {"type": "string", "enum": ["auto", "stock", "etf"], "default": "auto"}
    date_field = {"type": "string", "pattern": "^[0-9]{8}$", "description": "Date in YYYYMMDD format"}
    limit = {"type": "integer", "minimum": 1, "maximum": 500}
    definitions = [
        ("get_instrument_profile", "Resolve stock or ETF profile data.", {"symbol": symbol, "instrument_type": instrument_type}, ["symbol"]),
        ("get_realtime_quote", "Fetch one stock or ETF real-time quote with provider fallback.", {"symbol": symbol, "instrument_type": instrument_type}, ["symbol"]),
        (
            "get_company_business",
            "Fetch a stock company's business introduction and main-business composition.",
            {"symbol": symbol, "composition_limit": {"type": "integer", "minimum": 1, "maximum": 500, "default": 100}},
            ["symbol"],
        ),
        (
            "get_price_history",
            "Fetch normalized adjusted OHLCV history for a stock or ETF.",
            {
                "symbol": symbol,
                "start_date": date_field,
                "end_date": date_field,
                "adjust": {"type": "string", "enum": ["qfq", "hfq", "none"], "default": "qfq"},
                "period": {"type": "string", "enum": ["daily", "weekly", "monthly"], "default": "daily"},
                "instrument_type": instrument_type,
                "limit": {"type": "integer", "minimum": 1, "maximum": 2000, "default": 500},
                "include_incomplete_today": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include a current-day bar before the A-share close; false by default to avoid partial daily data",
                },
            },
            ["symbol"],
        ),
        ("get_stock_financials", "Fetch stock financial indicators.", {"symbol": symbol, "indicator": {"type": "string", "default": "按报告期"}, "limit": limit}, ["symbol"]),
        ("get_stock_valuation", "Fetch stock valuation data.", {"symbol": symbol, "limit": {"type": "integer", "minimum": 1, "maximum": 1000}}, ["symbol"]),
        ("get_stock_news", "Fetch recent stock news for discovery and risk scanning.", {"symbol": symbol, "limit": {"type": "integer", "minimum": 1, "maximum": 100}}, ["symbol"]),
        ("list_industries", "List EastMoney industry boards.", {"limit": {"type": "integer", "minimum": 1, "maximum": 1000}}, []),
        (
            "get_industry_snapshot",
            "Fetch industry board spot data, daily history, and constituents.",
            {
                "industry": {"type": "string", "minLength": 1, "maxLength": 64},
                "start_date": date_field,
                "end_date": date_field,
                "adjust": {"type": "string", "enum": ["qfq", "hfq", "none"], "default": "none"},
                "constituent_limit": {"type": "integer", "minimum": 1, "maximum": 500},
                "history_limit": {"type": "integer", "minimum": 1, "maximum": 2000},
            },
            ["industry"],
        ),
    ]
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {"type": "object", "properties": properties, "required": required, "additionalProperties": False},
            },
        }
        for name, description, properties, required in definitions
    ]


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    function = _FUNCTIONS.get(name)
    if function is None:
        raise ToolError(f"unknown tool: {name}; available tools: {', '.join(sorted(_FUNCTIONS))}")
    if not isinstance(arguments, dict):
        raise ToolError("arguments must be a JSON object")
    try:
        return function(**arguments)
    except TypeError as exc:
        raise ToolError(f"invalid arguments for {name}: {exc}") from exc
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(f"{name} failed: {exc}") from exc


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("schema", help="Print JSON function definitions")
    call = subparsers.add_parser("call", help="Call one function by name")
    call.add_argument("--name", required=True)
    call.add_argument("--arguments", default="{}", help="JSON object")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.command == "schema":
        print(json.dumps(get_tool_definitions(), ensure_ascii=False, indent=2))
        return 0
    try:
        arguments = json.loads(args.arguments)
        result = call_tool(args.name, arguments)
    except (json.JSONDecodeError, ToolError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
