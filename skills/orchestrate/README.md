# orchestrate

由 Claude 担任调度者，负责任务拆分、派发、验收与集成。执行者是另一台**执行机**上的 coding agent：`codex`、`claude`（Claude Code API 模式）、`grok`、`agy`。Claude 通过 computer MCP 的 `run_command` / `command_job` 在执行机上调用 **`acpx`（Agent Client Protocol）**，并配合 `git worktree` 按职责和难度派发任务。附带的薄封装脚本 `scripts/acpx-dispatch` 负责建 worktree 与会话、切换适配器权限模式、校验每一步，并提取 `stopReason` 与最终汇报。验收与合入由 Claude 完成（当前配方基于 `acpx 0.22.0` 验证）。

## 拓扑

| | Claude 所在主机 | 执行机 |
| --- | --- | --- |
| 项目目录 | 同一绝对路径挂载（共享） | 原始目录 |
| `acpx`、worker CLI、项目工具链 | 不需要 | 需要 |
| worktree（`$REPO-wt/<task>`）、`/tmp`、派发产物 | 看不到 | 存放在这里 |
| 任务文件 `$REPO/.git/orchestrate/<task>.md` | 用 Write 写入 | 由 `acpx-dispatch` 读取 |

`git`、`acpx`、`acpx-dispatch` 与项目检查命令一律在执行机上执行，长任务用后台 `run_command` 加 `command_job` 轮询。

## 安装

Claude 所在主机：

```bash
npx skills add wossoft/agent-skills --skill orchestrate --agent claude-code --global --yes
```

并确保 Claude 已接入 computer MCP，且项目目录已挂载到相同路径。

执行机：
- `git`、`jq`、Node.js >= 22.13、`acpx`（已验证 `0.22.0`）与官方 ACP 适配器：

```bash
npm install -g acpx@0.22.0 @agentclientprotocol/codex-acp@latest @agentclientprotocol/claude-agent-acp@latest
```

- 软链辅助脚本：`<本仓库>/skills/orchestrate/scripts/acpx-dispatch --install`（链接到 `~/.local/bin/acpx-dispatch`）。
- 在 `~/.acpx/config.json` 中注册 `codex-acp`、`claude-agent-acp`、`grok agent stdio`、`agy acp`，格式见 [references/routing.md](references/routing.md)。
- Claude Code 的 API 配置（`ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` 等）写在执行机 `~/.claude/settings.json` 的 `env` 中。`acpx` 默认不加载用户级设置，`acpx-dispatch` 会为 `claude` 自动设置 `ACPX_CLAUDE_INCLUDE_USER_SETTINGS=1`。因此执行机的用户级 Claude 设置里不要放会触发再派发的 hooks、插件或全局 `CLAUDE.md`。

在 Claude 的全局规则（如 `~/.claude/CLAUDE.md`）中加一行指针，可选附上个人 tier 模型映射（格式见 [references/routing.md](references/routing.md)）：

```markdown
- 非一两行的实现、诊断、调研或批量杂活，先加载 `orchestrate` skill，按其中的分工通过执行机派发与验收。
```

## 使用示例（以下命令都在执行机上，经 `run_command` 执行）

```bash
REPO="/path/to/repo"
TASK="fix-paging"
T="$REPO/.git/orchestrate/$TASK.md"   # Claude 在本机用 Write 写入

# 1. 可写任务：worktree 隔离 + 持久 ACP 会话（run_command background: true）
acpx-dispatch run codex "$TASK" "$T" --repo "$REPO" --effort high

# 返工续聊（复用记录的 worker、目录和权限参数，不重复传 --model）
acpx-dispatch revise "$TASK" "$REPO/.git/orchestrate/$TASK-rev.md" --repo "$REPO"

# 重新查看最近一轮的 stopReason、改动与最终汇报
acpx-dispatch report "$TASK" --repo "$REPO"

# 运行中按需查看状态或取消（WT 为脚本输出的 worktree 路径）
acpx --cwd "$WT" codex status -s "$TASK"
acpx --cwd "$WT" codex cancel -s "$TASK"

# 验收通过后生成补丁、合入主仓库并跑检查；全部成功后才关闭会话与清理 worktree
git -C "$WT" add -A &&
git -C "$WT" diff --cached --binary "$BASE" > "/tmp/$TASK.patch" &&
git -C "$REPO" apply --3way "/tmp/$TASK.patch" &&
acpx --cwd "$WT" codex sessions close "$TASK" &&
git -C "$REPO" worktree remove --force "$WT" &&
git -C "$REPO" branch -D "agent/$TASK"

# 2. 只读任务（诊断 / 审查 / 调研）：无状态 exec，并切到适配器自身的只读模式；改动工作区则退出 6
acpx-dispatch run codex review-paging "$REPO/.git/orchestrate/review-paging.md" --repo "$REPO" --mode read-only --effort xhigh
```

单测（使用假 acpx，不调用模型，在执行机上运行）：`python3 -m unittest discover -s skills/orchestrate/tests`

## 从旧版迁移

- `cc-api` worker 已废弃：`acpx-dispatch` 不再接受 `cc-api`，原先派给它的 UI / 文档类任务改派执行机上的 `claude`。可删除 `~/.acpx/config.json` 中的 `cc-api` 条目和 `~/.local/bin/cc-api-acp`。
- 调度者固定为 Claude，worker 统一在执行机上运行。任务文件从 `/tmp/<task>.md` 改到 `$REPO/.git/orchestrate/<task>.md`，以便两台机器都能看到。
- 更早的 `scripts/agent-run` 已由 `scripts/acpx-dispatch` 取代，产物目录为 `${TMPDIR:-/tmp}/acpx-dispatch/`。
