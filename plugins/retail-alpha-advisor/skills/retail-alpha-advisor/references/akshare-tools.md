# AKShare function tools

The Skill bundles a small, read-only tool registry in `scripts/akshare_tools.py`. It targets AKShare `>=1.17,<2.0` and records the actual installed version in every response.

## Calling modes

List JSON function schemas:

```bash
python scripts/akshare_tools.py schema
```

Call a function:

```bash
python scripts/akshare_tools.py call --name get_instrument_profile \
  --arguments '{"symbol":"600519","instrument_type":"stock"}'
```

Import into an Agent SDK or MCP wrapper:

```python
from akshare_tools import call_tool, get_tool_definitions

tool_schemas = get_tool_definitions()
result = call_tool("get_price_history", {"symbol": "510300"})
```

## Functions

- `get_instrument_profile`: stock metadata with EastMoney -> Xueqiu -> CNInfo fallback; ETF metadata with EastMoney -> Xueqiu fallback.
- `get_realtime_quote`: per-symbol real-time quote with EastMoney -> Xueqiu -> Sina fallback for stocks and EastMoney -> Xueqiu for ETFs.
- `get_company_business`: company business introduction from `stock_zyjs_ths`, with Xueqiu company information fallback, plus optional EastMoney main-business composition from `stock_zygc_em`.
- `get_price_history`: normalized stock OHLCV history with EastMoney -> Tencent -> Sina fallback; ETF history with EastMoney -> Tencent and an unadjusted Sina fallback.
- `get_stock_financials`: important financial indicators from `stock_financial_abstract_new_ths`, with an identified fallback to `stock_financial_analysis_indicator`.
- `get_stock_valuation`: valuation history/metrics from `stock_value_em`.
- `get_stock_news`: recent stock news from `stock_news_em`; use only for discovery and risk scanning.
- `list_industries`: EastMoney industry board list from `stock_board_industry_name_em`, with a disclosed 10jqka fallback.
- `get_industry_snapshot`: EastMoney industry spot data, history, and constituents, with 10jqka fallbacks for industry info and history when EastMoney is unavailable.

All functions return JSON-serializable objects. Large datasets are bounded by `limit` so Agent context does not grow without control.

Every fallback-capable response contains ordered `attempts`, `selected_provider`, `selected_function`, and any `component_errors`. A fallback is valid only when it preserves the requested semantics and adjustment mode.

## Data rules

- Pass six-digit A-share or ETF codes. Use `instrument_type` when automatic ETF/stock inference could be ambiguous.
- Dates use `YYYYMMDD` in tool calls. Tool output normalizes date-like values to ISO strings when AKShare exposes them as date objects.
- Use one adjustment mode consistently: `qfq`, `hfq`, or `none`. Do not compare prices produced with different modes.
- `get_price_history` excludes the current trading day's bar before 15:10 Asia/Shanghai by default because AKShare may expose an incomplete daily bar. Set `include_incomplete_today` only when the caller explicitly needs intraday partial data.
- Treat EastMoney industry boards as an EastMoney classification, not as CSRC or Shenwan classification.
- Treat financial, valuation, and news endpoints as aggregator/third-party evidence. Cross-check material claims against exchange filings or company reports when possible.
- Treat Sina as a low-priority fallback: AKShare documents warn that repeated real-time or historical calls can temporarily block the caller's IP. Do not poll it or retry it in a loop.
- An AKShare call can fail because an upstream site changed or throttled access. Preserve `component_errors`; do not convert a failed component into an empty factual claim.
