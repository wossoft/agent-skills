# orchestrate

按需把边界清楚、工作量足够大的实现交给 worker，由当前会话负责范围、审查和验收。
默认串行；小改动、需求探索和依赖连续观察的调试直接完成。无需安装全局身份规则。

## 安装

```bash
npx skills add git@gitlab.com:wossoft/agent-skills.git \
  --skill orchestrate --agent codex --global --yes
```

其他宿主使用其支持的 skill 安装方式。执行脚本需要 Bash、Python 3、POSIX 环境，
以及选定的 `claude`、`agy`、`grok` 或 `codex` CLI。使用哪个 worker 由能力、可用性和
用户偏好决定；没有适合的 worker 时由当前会话完成。

可直接调用安装目录的 `scripts/agent-run`，或从该目录运行：

```bash
./scripts/agent-run --install
```

默认创建 `~/.local/bin/agent-run` 符号链接；已存在的目标不会被覆盖。
确认该目录在 PATH 中。脚本依赖同目录的 Python 辅助脚本和上级目录的任务模板，
请保留完整 skill 目录。

## 使用

```bash
agent-run init-task api-fix --cwd /path/to/repo
# 填写输出路径中的任务书，然后执行：
agent-run claude /absolute/path/TASK.md --cwd /path/to/repo --timeout 1200
```

任务书位于 `~/.agents/tasks/<repo>/`，每次运行的独立目录位于 `~/.agents/runs/`。
可用 `AGENT_RUN_HOME` 修改存放位置。报告包含执行目录、退出码、worker 输出和前后
Git 快照（暂存/未暂存补丁、新文件路径及哈希）。新文件内容需要在工作目录中审查。
这些资料不是备份，忽略文件不在 Git 快照范围内。

默认保留权限控制。超时会终止 worker 进程组并返回 124；权限不足或超时后先检查
部分改动，再决定后续行动。退出码 0 不等于验收通过。

并行仅用于接口稳定、文件范围独立的任务；同仓库并行 CLI 工作使用 `--worktree`。
它要求原工作区干净，从 HEAD 创建分支，不复制忽略文件、依赖或本地配置。
宿主审查后负责集成并验证。不会自动提交、合并或删除 worktree。

修订会启动新会话：传入完整原任务、验收条件、修订意见和上次产物路径，并用
`--cwd <上次执行目录>`，不再添加 `--worktree`。

## 从旧版迁移

新版不需要 `references/identity.md` 常驻加载。旧版若已向全局规则复制 Session Lead，
更新 skill 不会自动移除它；经用户授权并备份后，仅移除当时复制的部分。
