# orchestrate

让任意主 agent（Claude Code、Codex、Grok 等）作为调度者：按职责和难度把任务派给其他
CLI agent（codex、claude、cc-api、grok、agy），再由主 agent 验收、集成。分工规则、派发流程
和验收要求都在 skill 里，全局规则只需要一行指针。

## 安装

```bash
npx skills add wossoft/agent-skills --skill orchestrate --agent codex --global --yes
```

其他宿主按各自方式安装 skill。脚本依赖 Bash、Git、`jq` 和所选 worker 的 CLI。

把 `agent-run` 链接到 PATH（目标已存在时不会覆盖）：

```bash
~/.agents/skills/orchestrate/scripts/agent-run --install   # -> ~/.local/bin/agent-run
```

在每个主 agent 的全局规则中加一行，例如写进 `~/.claude/CLAUDE.md` 或 `~/.codex/AGENTS.md`：

```markdown
- 非一两行的实现、诊断、调研或批量杂活，先加载 `orchestrate` skill，按其中的分工派发与验收。
```

## 个人配置

模型和思考等级的映射写在 `~/.config/agent-run/config`（Bash 格式，覆盖脚本默认值），
格式见 [references/routing.md](references/routing.md)。

## 使用

```bash
agent-run template > /tmp/task.md     # 填写任务书
agent-run codex fix-paging /tmp/task.md --repo . --tier complex --check "pnpm typecheck"
agent-run grok bump-deps /tmp/task.md --tier simple
agent-run agy research-x /tmp/task.md --mode plan
agent-run ls
```

- build 模式默认在 `<仓库>-wt/<任务名>` 的独立 worktree 中运行（基于 HEAD），并跳过权限确认；
  `--in-place` 在原工作区运行，保留权限控制；`--mode plan` 为只读。
- 产物在 `~/.agent-runs/<仓库>/<任务名>/`：`prompt.md`、`events.jsonl`、`final.md`、`status`、
  `changes.txt`、`patch.diff`、`check.log`。
- 退出码 0 只说明进程正常结束，验收以补丁和检查结果为准。脚本不会自动提交、合并或删除 worktree。
- worker 内再次调用 `agent-run` 会被拒绝。

## 测试

```bash
python3 -m unittest discover -s tests
```

测试使用假 worker 和临时仓库，不调用任何模型。

## 从旧版迁移

- 旧版接口 `agent-run <worker> TASK.md --cwd ...`、`init-task`、`--worktree` 已移除；现在默认使用 worktree，
  `--repo` 替代 `--cwd`。
- 旧版的 `references/identity.md` 和 Python 辅助脚本已删除。
- zcode 不再支持，改用 cc-api。
