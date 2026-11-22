# orchestrate

让任意主 agent（Claude Code、Codex、Grok 等）作为调度者：直接通过 **`acpx`（Agent Client Protocol）** 与 `git worktree` 按职责和难度把任务派给其他 coding agent（`codex`、`claude`、`cc-api`、`grok`、`agy`），再由主 agent 验收与集成。纯文档型 skill，无需额外包装脚本（当前配方基于 `acpx 0.22.0` 验证）。

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

- 在 `~/.acpx/config.json` 中注册所需适配器（如 `codex-acp`、`claude-agent-acp`、`cc-api` 本地封装、`grok agent stdio`、`agy acp`），格式见 [references/routing.md](references/routing.md)。
- 在每个主 agent 的全局规则中加一行指针（以及可选的个人 tier 模型映射，具体格式见 [references/routing.md](references/routing.md)），例如写进 `~/.claude/CLAUDE.md` 或 `~/.codex/AGENTS.md`：

```markdown
- 非一两行的实现、诊断、调研或批量杂活，先加载 `orchestrate` skill，按其中的分工派发与验收。
```

## 使用示例

```bash
# 1. 可写任务：worktree 隔离 + 持久 ACP 会话（全程使用同一绝对路径 "$WT"）
REPO="/path/to/repo"
TASK="fix-paging"
BASE=$(git -C "$REPO" rev-parse HEAD)
WT="$(cd "$(dirname "$REPO")" && pwd)/$(basename "$REPO")-wt/$TASK"

git -C "$REPO" worktree add -b "agent/$TASK" "$WT" "$BASE" &&
acpx --cwd "$WT" codex sessions new --name "$TASK" &&
acpx --cwd "$WT" codex set reasoning_effort high -s "$TASK" &&
acpx --cwd "$WT" --approve-all --non-interactive-permissions fail \
  --suppress-reads --timeout 1800 codex -s "$TASK" -f "/tmp/$TASK.md"

# 返工续聊（不重复传 --model，保持相同权限参数）
acpx --cwd "$WT" --approve-all --non-interactive-permissions fail \
  --suppress-reads --timeout 1800 codex -s "$TASK" -f "/tmp/$TASK-rev.md"

# 运行中按需查看状态 / 监控 / 取消（取消后需等待该轮收尾再验收）
acpx --cwd "$WT" codex status -s "$TASK"
acpx --cwd "$WT" --suppress-reads codex sessions watch -s "$TASK"
acpx --cwd "$WT" codex cancel -s "$TASK"

# 验收通过后生成补丁、合入主仓库并跑检查；全部成功后才关闭会话与清理 worktree
git -C "$WT" add -A &&
git -C "$WT" diff --cached --binary "$BASE" > "/tmp/$TASK.patch" &&
git -C "$REPO" apply --3way "/tmp/$TASK.patch" &&
acpx --cwd "$WT" codex sessions close "$TASK" &&
git -C "$REPO" worktree remove --force "$WT" &&
git -C "$REPO" branch -D "agent/$TASK"

# 2. 只读任务（诊断 / 审查 / 调研）：直接走无状态 acpx exec
acpx --cwd "$REPO" --approve-reads --non-interactive-permissions deny \
  --no-terminal --permission-policy '{"autoApprove":["read","search"],"defaultAction":"deny"}' \
  --suppress-reads --timeout 1800 \
  codex exec --config-option reasoning_effort=xhigh -f "/tmp/review.md"
```

## 从旧版迁移

- 移除 `scripts/agent-run` 包装脚本、`tests/` 及 `~/.agent-runs/` 统一产物归档，改为在 skill 文档中直接指导主 agent 组合使用 `acpx` 与 `git worktree`。
- 旧用户可自行删除 `~/.local/bin/agent-run` 软链；原先写在 `~/.config/agent-run/config` 中的适配器命令迁入 `~/.acpx/config.json`，`TIER_*` 模型映射迁入个人全局规则（如 `~/.claude/CLAUDE.md` 或 `~/.codex/AGENTS.md`）。
