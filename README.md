# Wossoft Agent Skills

Wossoft 内部 Agent Skills 与 Codex Plugins 发布仓库。

## 安装 Retail Alpha Advisor

首次添加私有 Marketplace：

```bash
codex plugin marketplace add git@gitlab.com:wossoft/agent-skills.git
```

安装插件：

```bash
codex plugin add retail-alpha-advisor@wossoft-agent-skills
```

也可以在 Codex 中打开 `/plugins`，切换到 `Wossoft Agent Skills` 后安装 `Retail Alpha Advisor`。

安装或升级后使用新会话调用：

```text
$retail-alpha-advisor
```

## 运行依赖

- Python 3.12+
- `uv`
- AKShare `>=1.17,<2.0`，首次调用时由 Skill 使用 `uv run --with` 准备

插件只生成研究和人工决策建议，不执行交易。所有输出以“市场有风险，投资需谨慎。”结尾。

## 仓库结构

```text
.agents/plugins/marketplace.json
.agents/skills/retail-alpha-advisor -> plugin skill
plugins/retail-alpha-advisor/
  .codex-plugin/plugin.json
  skills/retail-alpha-advisor/
```
