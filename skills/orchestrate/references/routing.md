# Routing and tiers

## Workers

| Worker | CLI | Notes |
| --- | --- | --- |
| `codex` | `codex exec` | Sandbox `workspace-write` (build) or `read-only` (plan). Final report via `-o`. |
| `claude` | `claude -p` | Native Claude Code with the user's normal config. |
| `cc-api` | `claude -p` with `CLAUDE_CONFIG_DIR=$CC_API_CONFIG_DIR` | Claude Code backed by another API (for example GLM). `--effort` only `low`, `high`, `max`. Medium-complexity work only; map every tier to the same mid-size model. |
| `grok` | `grok -p` | |
| `agy` | `agy -p` | Model fixed by agy's own settings; `--model` / `--effort` rejected. |

Permissions: in an isolated worktree, build mode skips approvals
(`--dangerously-skip-permissions` / `--always-approve`; Codex keeps its sandbox).
`--in-place` keeps permission controls (Claude uses `acceptEdits`). Plan mode is
read-only for every worker.

## Tiers

`--tier hard|complex|simple|cu` maps to a model and reasoning effort per worker.
`--model` and `--effort` override the tier. Built-in defaults only set effort and
leave the model to each CLI:

| Worker | hard | complex | simple | cu |
| --- | --- | --- | --- | --- |
| codex | xhigh | high | medium | xhigh |
| claude / cc-api | max | high | CLI default | high |
| grok | high | high | CLI default | high |

## User overrides

agent-run sources `${AGENT_RUN_CONFIG:-~/.config/agent-run/config}` as Bash after
the defaults. Each entry is `TIER_<worker>_<tier>="<model|-> <effort|->"`, with `-`
in worker names written as `_`. Example:

```bash
TIER_codex_hard="<codex-strongest-model> medium"
TIER_codex_complex="<codex-main-model> high"
TIER_codex_simple="<codex-fast-model> medium"
TIER_codex_cu="<codex-fast-model> xhigh"
TIER_grok_simple="<grok-fast-model> -"
TIER_cc_api_complex="<cc-api-model> high"
TIER_cc_api_hard="<cc-api-model> high"
CC_API_CONFIG_DIR="$HOME/.claude-api"
```

`codex` `hard` is the second brain (read-only cross-checks); `complex` handles
both medium and complex implementation. `DEFAULT_TIER_<worker>` changes a worker's
default tier (built-in default `complex`).

Role preferences beyond the defaults in SKILL.md belong in the user's own global
rules or the repository's instructions; the orchestrator follows those first.
