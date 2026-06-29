---
name: retail-alpha-advisor
description: Evaluate existing A-share and ETF holdings, research candidate stocks, ETFs, or industries, and produce evidence-backed position signals with explicit risk gates. Use when an agent needs to answer whether to hold, add, reduce, or exit an existing position; assess portfolio concentration or industry exposure; analyze a future holding candidate; or turn Tencent westockdata market, financial, valuation, fund-flow, ETF, and industry data into an auditable manual-trading recommendation.
---

# Retail Alpha Advisor

Use the Tencent-provided `westockdata` skill for market data, then produce research and position recommendations. Keep all execution manual. Never place orders or present model judgment as market fact.

This skill owns analysis, evidence normalization, risk gates, and recommendation wording. It does not own data scraping, provider fallback logic, or local market-data wrappers.

## Select the workflow

- Use `portfolio-review` for existing holdings, portfolio concentration, industry exposure, cash level, or a hold/add/reduce/exit question.
- Use `research` for a stock, ETF, or industry that is not yet held, including watchlist scans and prospective position signals.
- Run both workflows separately when the request mixes current holdings and new candidates. Do not blend their evidence or action labels.

## Collect data with westockdata

Read [references/westockdata-data.md](references/westockdata-data.md), then use the `westockdata` skill for only the data needed by the request.

```bash
npx -y westock-data-clawhub@1.0.4 kline sh600519 --period day --limit 121
npx -y westock-data-clawhub@1.0.4 finance sh600519 --num 4
npx -y westock-data-clawhub@1.0.4 technical sh600519 --group ma,macd,rsi
```

1. For `portfolio-review`, obtain holdings, cost prices, weights, cash, and risk limits from the user. westockdata cannot know the user's portfolio.
2. Convert user symbols to westockdata format before querying: `sh600000`, `sz000001`, `bj430047`, `hk00700`, or `usAAPL`.
3. Resolve each instrument and fetch daily prices. Fetch profile, finance, valuation/technical, fund-flow, ETF holdings/NAV, or industry data only when the holding thesis depends on that dimension.
4. For `research`, fetch the target profile, price history, and, for stocks, finance/valuation/business evidence. For ETFs, fetch ETF detail, holdings, NAV, holder/concentration data when available. Fetch industry or board data for industry context.
5. Preserve every command's provider (`westockdata`), package (`westock-data-clawhub@1.0.4` when used), command name, retrieval time, parameters, latest data date, and currency/unit notes.
6. If westockdata lacks a field or fails, record the gap. Do not recreate a local scraper or fall back to AKShare inside this skill.

## Build the evidence pack

Normalize holdings plus westockdata responses into [references/input-schema.md](references/input-schema.md). Keep facts, deterministic calculations, and agent judgments separate. Never invent unavailable fields.

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
- Do not claim that westockdata, Tencent, or their upstream public-market sources are authoritative company filings.
- Cross-check material company conclusions against primary disclosures when retrieval tools are available; otherwise state that the conclusion uses aggregator data only.
- Do not infer missing cost basis, cash, holdings, industry classification, or risk limits.
- Do not add back bundled market-data collection scripts to this skill unless the user explicitly reverses the westockdata boundary.
- End with `市场有风险，投资需谨慎。`
