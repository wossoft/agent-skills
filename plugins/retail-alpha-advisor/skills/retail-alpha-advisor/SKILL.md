---
name: retail-alpha-advisor
description: Evaluate existing A-share and ETF holdings, research candidate stocks, ETFs, or industries, and produce evidence-backed position signals with explicit risk gates. Use when an agent needs to answer whether to hold, add, reduce, or exit an existing position; assess portfolio concentration or industry exposure; analyze a future holding candidate; or turn AKShare market, financial, valuation, news, and industry data into an auditable manual-trading recommendation.
---

# Retail Alpha Advisor

Use AKShare-backed functions to collect evidence, then produce research and position recommendations. Keep all execution manual. Never place orders or present model judgment as market fact.

## Select the workflow

- Use `portfolio-review` for existing holdings, portfolio concentration, industry exposure, cash level, or a hold/add/reduce/exit question.
- Use `research` for a stock, ETF, or industry that is not yet held, including watchlist scans and prospective position signals.
- Run both workflows separately when the request mixes current holdings and new candidates. Do not blend their evidence or action labels.

## Collect data with the bundled functions

Read [references/akshare-tools.md](references/akshare-tools.md), then call only the functions needed for the request. The callable registry and JSON schemas are in `scripts/akshare_tools.py`.

```bash
uv run --with 'akshare>=1.17,<2.0' \
  python .agents/skills/retail-alpha-advisor/scripts/akshare_tools.py schema

uv run --with 'akshare>=1.17,<2.0' \
  python .agents/skills/retail-alpha-advisor/scripts/akshare_tools.py call \
  --name get_price_history \
  --arguments '{"symbol":"600519","start_date":"20250101","end_date":"20260629"}'
```

Another agent runtime may import `get_tool_definitions()` and `call_tool(name, arguments)` directly and expose them as native function tools.

1. For `portfolio-review`, obtain holdings, cost prices, weights, cash, and risk limits from the user. AKShare cannot know the user's portfolio.
2. Resolve each instrument and fetch adjusted daily prices. Fetch stock company/business information, financials, and valuation when the holding thesis depends on company fundamentals.
3. For `research`, fetch the target profile, company/business information, price history, and, for stocks, financials and valuation. Fetch industry constituents/history for industry context. News is a secondary discovery source, not authoritative evidence.
4. Preserve every tool response's AKShare version, underlying function, upstream label, retrieval time, parameters, and latest data date.
5. Use the configured same-semantics provider chain when an endpoint fails. Preserve ordered `attempts`, the failure reason, `selected_provider`, and `selected_function`; never switch source silently.

## Build the evidence pack

Normalize holdings plus tool responses into [references/input-schema.md](references/input-schema.md). Keep facts, deterministic calculations, and agent judgments separate. Never invent unavailable fields.

Run:

```bash
python3 .agents/skills/retail-alpha-advisor/scripts/build_evidence.py \
  --mode portfolio-review \
  --input /path/to/snapshot.json \
  --output /tmp/retail-alpha-evidence.json
```

Use `--mode research` for a future holding. Read the JSON output before writing a recommendation. For deterministic tests, `--today YYYY-MM-DD` overrides the current date.

## Apply the decision gates

- Treat price trend, return, volatility, drawdown, valuation, fundamentals, industry conditions, and portfolio fit as separate evidence dimensions.
- Do not turn a descriptive technical state, third-party valuation score, research report, or news item into a trade signal by itself.
- Give a position range only when `readiness.position_sizing_ready` is true. Otherwise identify the missing risk-policy fields and use `观察` or `等待`.
- For industry research, do not give a position signal until the exposure is mapped to a tradable stock or ETF with its own price and liquidity evidence.
- Treat a hard risk-policy breach as stronger than a bullish narrative. A breached single-position, industry, or cash limit blocks adding exposure.
- Distinguish the latest market date, financial report period, retrieval time, and proposed action date. Reject stale inputs instead of silently treating them as current.
- Never use `强烈买入`, guaranteed-return language, or false precision.

## Produce the recommendation

Follow [references/output-contract.md](references/output-contract.md). Use exactly one action per evaluated position:

`保持`、`观察`、`等待`、`小仓试探`、`加仓`、`减仓`、`退出`

Support the action with objective evidence, opposing evidence, invalidation conditions, and data gaps. Explicitly label judgment and uncertainty.

For existing holdings, compare the latest position weight with both portfolio constraints and the evidence for the instrument. For future holdings, first decide whether the thesis is research-ready, then whether it is signal-ready, and only then whether it is position-size-ready.

## Preserve the boundary

- Do not trade, connect to a broker, store credentials, or modify any application/database state.
- Do not claim that AKShare or its upstream sites are authoritative company filings.
- Cross-check material company conclusions against primary disclosures when retrieval tools are available; otherwise state that the conclusion uses aggregator data only.
- Do not infer missing cost basis, cash, holdings, industry classification, or risk limits.
- End with `市场有风险，投资需谨慎。`
