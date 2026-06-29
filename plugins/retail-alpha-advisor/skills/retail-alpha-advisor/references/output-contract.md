# Output contract

Return concise Markdown with this order.

## 结论

- `数据截止` and `建议适用日`
- evaluated portfolio, holding, stock, ETF, or industry
- exactly one action: `保持`、`观察`、`等待`、`小仓试探`、`加仓`、`减仓`、`退出`
- position range only when the risk gate allows it
- confidence: `低`、`中`、`高`

## 证据

Separate:

1. deterministic portfolio and market facts;
2. current fundamental or industry facts with citations;
3. agent judgment derived from those facts.

Do not describe a technical state as proof of future returns.

## 反方证据与风险

Give the strongest evidence against the recommendation. Include concentration, liquidity, event, valuation, data-quality, and model-risk issues when applicable.

## 失效条件

State observable conditions that would invalidate the conclusion. Use dates, report periods, prices, trend states, or business events when supported by the snapshot. Do not invent precise thresholds.

## 数据缺口

Copy material gaps from the evidence pack. If position sizing is blocked, explicitly say why.

## 追溯信息

Include snapshot ID, data-as-of date, input hash, Skill name/version if available, risk-policy version, and source dates. End with:

`市场有风险，投资需谨慎。`
