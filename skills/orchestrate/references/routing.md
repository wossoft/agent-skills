# Routing and tiers

## Workers

Drive every worker directly through `acpx` (verified against `acpx 0.22.0`). Configure
custom/local adapters in `~/.acpx/config.json` and call `<worker>` by positional
name (not `--agent "env ..."`). Note that a project-level `<cwd>/.acpxrc.json`
overrides global `~/.acpx/config.json` settings (`agents`, `mcpServers`, etc.).

| Worker | `acpx` Agent (`~/.acpx/config.json`) | Effort Config Key | Notes |
| --- | --- | --- | --- |
| `codex` | `codex` (`codex-acp`) | `reasoning_effort` | Supports `--model` and `reasoning_effort` (`low`/`medium`/`high`/`xhigh`/`max`, subject to model options). |
| `claude` | `claude` (`claude-agent-acp`) | `effort` | Native Claude Code (`low`/`medium`/`high`/`max`, subject to model options). `acpx` isolates Claude user settings by default (`settingSources: ["project", "local"]`); set `ACPX_CLAUDE_INCLUDE_USER_SETTINGS=1` only when user-level settings are explicitly needed. |
| `cc-api` | `cc-api` (local wrapper -> `claude-agent-acp`) | `effort` | Claude Code backed by another API (for example GLM). Configure `cc-api` in `~/.acpx/config.json` to invoke a local wrapper that exports `.env` keys from `$CC_API_CONFIG_DIR/settings.json` and sets `CLAUDE_CONFIG_DIR` before `exec claude-agent-acp`. Because a custom wrapper name bypasses `acpx`'s built-in `claude-agent-acp` detection (`settingSources` / `_meta.systemPrompt`), isolation relies on `CLAUDE_CONFIG_DIR`. Effort values for GLM: `low`, `high`, `max`. Medium-complexity work only; never assign `hard` tier. |
| `grok` | `grok` (`grok agent stdio`) | `reasoning_effort` | Supports `--model` and `reasoning_effort` (`low`/`medium`/`high`/`xhigh`). Configure directly as `["grok", "agent", "stdio"]` in `~/.acpx/config.json` (do not wrap in `env ...`, which breaks `acpx`'s built-in Grok auth detection). |
| `agy` | `agy` (`agy acp` or built-in `antigravity`) | — | Model fixed by agy's own settings; omit `--model` and effort options. |

## Permissions

Always place global flags before `<worker>`, pass `--suppress-reads` (note:
`--suppress-reads` only filters stdout/JSON display; pass it on `sessions watch` too
if desired), and set an explicit `--timeout` (`1800` seconds is a recipe convention;
otherwise `acpx` reads config `timeout` or applies no CLI timeout):

- **Isolated worktree (writable default)**:
  `--approve-all --non-interactive-permissions fail`
- **In-place (writable, serial only)**:
  `--approve-reads --non-interactive-permissions deny --no-terminal --no-fs --permission-policy '{"autoApprove":["read","search","edit","delete","move"],"defaultAction":"deny"}'`
  - Pass these exact permission flags on `sessions new`, initial prompt, and any
    in-place revisions so the queue owner and turns share one boundary.
  - Why `--no-fs` and `--no-terminal`: in `acpx`, `--permission-policy` only governs
    `session/request_permission`, whereas ACP `fs/write_text_file` and
    `terminal/create` obey the top-level permission mode separately (`--approve-reads`
    + `deny` would otherwise reject ACP `fs/write_text_file`). Disabling ACP
    fs/terminal callbacks routes file edits through the agent's own tools under
    `--permission-policy`.
  - Adapter caveat: whether an adapter's native tools honor `--permission-policy` or
    instead bypass ACP permissions (or require `fs/write_text_file` and refuse writes)
    depends on the adapter. Use in-place only when the adapter honors this boundary;
    otherwise prefer an isolated worktree instead of loosening permissions.
- **Read-only (`exec`)**:
  `--approve-reads --non-interactive-permissions deny --no-terminal --permission-policy '{"autoApprove":["read","search"],"defaultAction":"deny"}'`
  - `defaultAction: deny` ensures non-read ACP permission requests are denied even if
    a TTY is present. Note that adapter-native tools and MCP remain governed by the
    adapter's own sandbox/read-only mode.

## Tiers

Default effort mapping per tier and worker (leave `--model` omitted unless overridden
by the user's global or repository model table, and defer to actual `configOptions`
advertised by the adapter/model):

| Worker | `hard` | `complex` | `simple` | `cu` |
| --- | --- | --- | --- | --- |
| `codex` | `xhigh` | `high` | `medium` | `xhigh` |
| `claude` / `cc-api` | `max` | `high` | adapter default | `high` |
| `grok` | `high` | `high` | adapter default | `high` |

`codex` at `hard` tier is the second brain (read-only cross-checks); `complex`
handles both medium and complex implementation.

How to pass model and effort in `acpx`:

- **Persistent session (writable tasks)**: pass `--model "<model>"` ONLY on
  `sessions new --name "$TASK"`, set effort with
  `acpx --cwd "$WT" <worker> set <effort-key> <effort> -s "$TASK"`, then send prompts
  with `-s "$TASK"` without re-passing `--model` (so `acpx` preserves
  `desired_config_options`). Verify stdout on both `sessions new` (confirms
  `created session` / UUID) and `set` (confirms `config set:`) rather than relying
  on `&&` / exit code alone — in `acpx 0.22.0`, an unsupported `--model` on
  `sessions new` and a rejected `set` value both print an error while exiting `0`.
- **Stateless one-shot (`exec`, read-only tasks)**:
  `acpx ... [--model "<model>"] <worker> exec [--config-option <effort-key>=<effort>] -f "/tmp/$TASK.md"`.

## Personal configuration

Register adapters in `~/.acpx/config.json`:

```json
{
  "agents": {
    "codex": { "argv": ["codex-acp"] },
    "claude": { "argv": ["claude-agent-acp"] },
    "cc-api": { "argv": ["/path/to/.local/bin/cc-api-acp"] },
    "grok": { "argv": ["grok", "agent", "stdio"] },
    "agy": { "argv": ["agy", "acp"] }
  }
}
```

Example local wrapper (`~/.local/bin/cc-api-acp`, `chmod +x`) so `cc-api` loads
`.env` from `$CC_API_CONFIG_DIR/settings.json` and fails closed if configuration or
credentials are missing:

```bash
#!/usr/bin/env bash
set -euo pipefail
export CLAUDE_CONFIG_DIR="${CC_API_CONFIG_DIR:-$HOME/.claude-api}"
settings="$CLAUDE_CONFIG_DIR/settings.json"
[ -f "$settings" ] || { echo "cc-api-acp: missing $settings" >&2; exit 1; }
env_exports=$(jq -er '
  .env // {} | to_entries[]
  | select((.key | test("^[A-Za-z_][A-Za-z0-9_]*$")) and .value != null)
  | "export \(.key)=\(.value | tostring | @sh)"
' "$settings")
[ -n "$env_exports" ] || { echo "cc-api-acp: no .env entries in $settings" >&2; exit 1; }
eval "$env_exports"
: "${ANTHROPIC_AUTH_TOKEN:?cc-api-acp: missing ANTHROPIC_AUTH_TOKEN in $settings}"
exec claude-agent-acp "$@"
```

Personal tier -> model ID mappings and role overrides belong in the user's own global
agent rules (for example `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`) or repository
instructions, which the orchestrator follows first. Example mapping using placeholders:

```markdown
- `orchestrate` 模型映射：
  - `codex`: hard=`<codex-strongest-model>` (reasoning_effort=medium), complex=`<codex-main-model>` (high), simple=`<codex-fast-model>` (medium), cu=`<codex-fast-model>` (xhigh)
  - `grok`: simple=`<grok-fast-model>`
  - `cc-api`: all=`<cc-api-model>` (high)
```
