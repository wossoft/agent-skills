# orchestrate

让任意主 agent（Claude Code、Codex、Grok 等）作为调度者：直接通过 **`acpx`（Agent Client Protocol）** 与 `git worktree` 按职责和难度把任务派给其他 coding agent（`codex`、`claude`、`cc-api`、`grok`、`agy`），再由主 agent 验收与集成。附带一个薄封装脚本 `scripts/acpx-dispatch`，负责建 worktree / 会话、切换适配器权限模式、校验每一步并提取 `stopReason` 与最终汇报；验收与合入仍由主 agent 完成（当前配方基于 `acpx 0.22.0` 验证）。

## 安装

```bash
npx skills add wossoft/agent-skills --skill orchestrate --agent codex --global --yes
```

其他宿主按各自方式安装 skill。依赖：
- `git`（以及 `jq`，用于 `cc-api` 本地封装脚本安全读取 `.env`）
- Node.js >= 22.13、`acpx`（已验证 `0.22.0`）与官方 ACP 适配器：

```bash
npm install -g acpx@0.22.0 @agentclientprotocol/codex-acp@latest @agentclientprotocol/claude-agent-acp@latest
```

- 软链辅助脚本：`skills/orchestrate/scripts/acpx-dispatch --install`（链接到 `~/.local/bin/acpx-dispatch`）。
- 在 `~/.acpx/config.json` 中注册所需适配器（如 `codex-acp`、`claude-agent-acp`、`cc-api` 本地封装、`grok agent stdio`、`agy acp`），格式见 [references/routing.md](references/routing.md)。
- 在每个主 agent 的全局规则中加一行指针（以及可选的个人 tier 模型映射，具体格式见 [references/routing.md](references/routing.md)），例如写进 `~/.claude/CLAUDE.md` 或 `~/.codex/AGENTS.md`：

```markdown
- 非一两行的实现、诊断、调研或批量杂活，先加载 `orchestrate` skill，按其中的分工派发与验收。
```

## 使用示例

```bash
REPO="/path/to/repo"
TASK="fix-paging"

# 1. 可写任务：worktree 隔离 + 持久 ACP 会话（--ttl 3600，验收期间返工仍续用原会话）
acpx-dispatch run codex "$TASK" "/tmp/$TASK.md" --repo "$REPO" --effort high

# 返工续聊（复用记录的 worker / 目录 / 权限参数，不重复传 --model）
acpx-dispatch revise "$TASK" "/tmp/$TASK-rev.md" --repo "$REPO"

# 重新查看最近一轮的 stopReason、改动与最终汇报
acpx-dispatch report "$TASK" --repo "$REPO"

# 运行中按需查看状态 / 取消（WT 为脚本输出的 worktree 路径）
acpx --cwd "$WT" codex status -s "$TASK"
acpx --cwd "$WT" codex cancel -s "$TASK"

# 验收通过后生成补丁、合入主仓库并跑检查；全部成功后才关闭会话与清理 worktree
git -C "$WT" add -A &&
git -C "$WT" diff --cached --binary "$BASE" > "/tmp/$TASK.patch" &&
git -C "$REPO" apply --3way "/tmp/$TASK.patch" &&
acpx --cwd "$WT" codex sessions close "$TASK" &&
git -C "$REPO" worktree remove --force "$WT" &&
git -C "$REPO" branch -D "agent/$TASK"

# 2. 只读任务（诊断 / 审查 / 调研）：无状态 exec，并切到适配器自身只读模式；改动工作区则退出 6
acpx-dispatch run codex review-paging "/tmp/review.md" --repo "$REPO" --mode read-only --effort xhigh
```

单测（使用假 acpx，不调用模型）：`python3 -m unittest discover -s skills/orchestrate/tests`

## 从旧版迁移

- `scripts/agent-run` 由 `scripts/acpx-dispatch` 取代：底层改为 `acpx`，产物目录从 `~/.agent-runs/` 改为 `${TMPDIR:-/tmp}/acpx-dispatch/`，不再内置 `--check`（检查由主 agent 在验收时执行）。
- 旧用户可自行删除 `~/.local/bin/agent-run` 软链；原先写在 `~/.config/agent-run/config` 中的适配器命令迁入 `~/.acpx/config.json`，`TIER_*` 模型映射迁入个人全局规则（如 `~/.claude/CLAUDE.md` 或 `~/.codex/AGENTS.md`）。
