# westockdata data collection

Use the Tencent-provided `westockdata` skill as the market-data provider for this advisor. Do not call AKShare or maintain local scraper code from this skill.

## Source skill

When available, read the `westockdata` skill's `SKILL.md` for the complete command list, field meanings, limitations, and safety notes. The expected package is:

```bash
npx -y westock-data-clawhub@1.0.4 <command> ...
```

westockdata supports A-share, HK, and US stocks, indices, ETFs, K-line/minute data, finance statements, fund flows, technical indicators, chip analysis, shareholders, dividends, ETF detail/holdings/NAV, boards, calendars, IPOs, and related market data.

## Symbol format

Use westockdata symbols:

| Market | Format | Example |
| --- | --- | --- |
| Shanghai / STAR | `sh` + 6 digits | `sh600000`, `sh688981` |
| Shenzhen | `sz` + 6 digits | `sz000001` |
| Beijing | `bj` + 6 digits | `bj430047` |
| Hong Kong | `hk` + 5 digits | `hk00700` |
| United States | `us` + ticker | `usAAPL` |

For user-facing output, keep the user's original symbol/name when useful, but store the queried westockdata symbol in provenance.

## Minimum query sets

For `portfolio-review`:

- Query `kline` with at least 121 daily bars for each holding when a 20/60/120-day evidence set is needed.
- Query `quote` or the latest `kline` row for the current market price when the user did not provide a trusted market price.
- Query stock `finance`, `profile`, `technical`, and `asfund` only when the thesis depends on fundamentals, company profile, technical state, or fund flow.
- Query ETF `etf`, `etf-holdings`, and `etf-nav` when reviewing ETF exposure, concentration, or NAV history.

For `research`:

- Stock: query `profile`, `kline`, `finance`, `technical`, and fund-flow data when relevant.
- ETF: query `etf`, `etf-holdings`, `etf-nav`, and price/technical data.
- Industry or board: query `board`, board K-line, board constituents, or ranking commands supported by westockdata. Do not produce a position signal until the analysis maps to a tradable stock or ETF.

## Common commands

```bash
npx -y westock-data-clawhub@1.0.4 search 贵州茅台
npx -y westock-data-clawhub@1.0.4 quote sh600519,sh510300
npx -y westock-data-clawhub@1.0.4 kline sh600519 --period day --limit 121
npx -y westock-data-clawhub@1.0.4 finance sh600519 --num 4
npx -y westock-data-clawhub@1.0.4 profile sh600519
npx -y westock-data-clawhub@1.0.4 asfund sh600519
npx -y westock-data-clawhub@1.0.4 technical sh600519 --group ma,macd,rsi
npx -y westock-data-clawhub@1.0.4 etf sh510300
npx -y westock-data-clawhub@1.0.4 etf-holdings sh510300
npx -y westock-data-clawhub@1.0.4 etf-nav sh510300 --start 2026-01-01 --end 2026-06-29
```

## Data rules

- `search` and `minute` are not batch commands; most other query commands accept comma-separated symbols.
- Keep currency and unit labels. HK and US data may not be in RMB; do not print `¥` for non-RMB fields.
- Use one price-adjustment basis consistently when comparing price history. If the command output does not expose the adjustment basis, state that gap.
- Treat finance, valuation, technical, fund-flow, board, news, and ETF data as aggregator evidence. Cross-check material company conclusions against filings when retrieval tools are available.
- If a command fails, returns no data, or lacks a needed field, record a data gap. Do not replace it with a local scraper.

## Provenance mapping

Copy each command into `sources`:

- `provider`: `westockdata`
- `provider_version`: `westock-data-clawhub@1.0.4` when the command used that package
- `command`: command name such as `kline`, `finance`, `technical`, `etf-holdings`
- `parameters`: symbol, period, limit, date range, adjustment mode, and other material flags when available
- `data_date`: latest observation/report date when visible
- `retrieved_date`: current date in `YYYY-MM-DD`
- `upstream`: `Tencent 自选股数据接口` when known from the westockdata skill
