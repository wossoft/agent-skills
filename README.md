# Wossoft Agent Skills

Wossoft 维护的 Agent Skills，适用于 Codex、Claude Code 等支持 skill 的 agent。

## Skills

| Skill | 用途 |
| --- | --- |
| [abp-ddd-module-designer](skills/abp-ddd-module-designer/SKILL.md) | ABP DDD 业务模块设计、审查、重构与代码骨架生成。 |
| [seo-content-architect](skills/seo-content-architect/SKILL.md) | 在 UI 设计与开发前，完成基于真实 SERP 的网站身份、内容架构、页面规划与内部链接设计。 |
| [orchestrate](skills/orchestrate/SKILL.md) | 让任意主 agent 按职责和难度把任务派给 codex / claude / cc-api / grok / agy，并负责验收与集成。 |
| [page-blueprint](skills/page-blueprint/SKILL.md) | 新页面从 0 到 1 时，用目录 + Markdown/YAML 描述页面布局、跳转与弹层（组件直接使用 shadcn/ui 等组件库名称）；已有页面的迭代直接改代码。 |

## 安装

使用 [`npx skills`](https://github.com/vercel-labs/skills) 安装，`--skill` 指定要安装的 skill，`--agent` 指定目标 agent：

```bash
npx skills add wossoft/agent-skills --skill orchestrate --agent codex --global --yes
```

查看仓库中可安装的 skill：

```bash
npx skills add wossoft/agent-skills --list
```

安装后重新开启 agent 会话即可使用。

- `orchestrate` 的 `agent-run` 安装、个人模型配置及迁移说明见 [skills/orchestrate/README.md](skills/orchestrate/README.md)。
- `page-blueprint` 的格式示例见 [skills/page-blueprint/references/example/](skills/page-blueprint/references/example/)。

## License

[MIT](LICENSE)
