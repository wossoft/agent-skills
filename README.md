# Wossoft Agent Skills

Wossoft 内部 Agent Skills 与 Codex Plugins 发布仓库。

## Skills

| Skill | 用途 |
| --- | --- |
| [abp-ddd-module-designer](skills/abp-ddd-module-designer/SKILL.md) | ABP DDD 业务模块设计、审查、重构与代码骨架生成。 |
| [seo-content-architect](skills/seo-content-architect/SKILL.md) | 在 UI 设计与开发前，完成基于真实 SERP 的网站身份、内容架构、页面规划与内部链接设计。 |
| [orchestrate](skills/orchestrate/SKILL.md) | 按需委派边界清楚的实现任务，默认串行，由当前会话负责审查、集成和验收。 |

## 安装

使用 `npx skills` 从 GitLab 仓库全局安装到 Codex。

安装 `abp-ddd-module-designer`：

```bash
npx skills add git@gitlab.com:wossoft/agent-skills.git \
  --skill abp-ddd-module-designer \
  --agent codex \
  --global \
  --yes
```

安装 `seo-content-architect`：

```bash
npx skills add git@gitlab.com:wossoft/agent-skills.git \
  --skill seo-content-architect \
  --agent codex \
  --global \
  --yes
```

Skill 将安装到 `~/.codex/skills/<skill-name>`。私有仓库需要本机已配置 GitLab SSH 访问权限。安装后重新开启 Codex 会话即可使用。

安装 `orchestrate`：

```bash
npx skills add git@gitlab.com:wossoft/agent-skills.git \
  --skill orchestrate \
  --agent codex \
  --global \
  --yes
```

按需派工、`agent-run` 的安装及旧版身份规则迁移说明见 [skills/orchestrate/README.md](skills/orchestrate/README.md)。

如需先查看仓库中可安装的 Skills：

```bash
npx skills add git@gitlab.com:wossoft/agent-skills.git --list
```

### 维护说明

`skills/abp-ddd-module-designer/` 是该 skill 在本仓库中的维护目录，包含 `SKILL.md` 入口，以及 `references/` 中按需读取的审查指南和模块布局参考。

初始内容来自本机已安装的 `~/.codex/skills/abp-ddd-module-designer-skill/`，现已精简重复规则和固定输出模板。本仓库的修改不会自动同步到本机安装目录；更新后需要同步或重新安装才能生效。
