# Routing and tiers

Everything in this file runs on the **executor machine** (via the computer MCP's
`run_command`), where `acpx`, the adapters, and `~/.acpx/config.json` live. See
"Executor machine" in [../SKILL.md](../SKILL.md).

## Workers

Drive every worker directly through `acpx` (verified against `acpx 0.22.0`). Configure
custom/local adapters in `~/.acpx/config.json` and call `<worker>` by positional
name (not `--agent "env ..."`). Note that a project-level `<cwd>/.acpxrc.json`
overrides global `~/.acpx/config.json` settings (`agents`, `mcpServers`, etc.).

| Worker | `acpx` Agent (`~/.acpx/config.json`) | Effort Config Key | Notes |
| --- | --- | --- | --- |
| `codex` | `codex` (`codex-acp`) | `reasoning_effort` | Supports `--model` and `reasoning_effort` (`low`/`medium`/`high`/`xhigh`/`max`, subject to model options). |
| `claude` | `claude` (`claude-agent-acp`) | `effort` | Claude Code on the executor, configured for API mode there (its own API key, model, and quota; no wrapper needed). Medium-complexity work only; never assign `hard` tier. Effort values (`low`/`medium`/`high`/`max`, subject to model options). `acpx` isolates Claude user settings by default (`settingSources: ["project", "local"]`), which drops the API `env` in the executor's `~/.claude/settings.json` and fails with `Authentication required` (verified). `acpx-dispatch` therefore exports `ACPX_CLAUDE_INCLUDE_USER_SETTINGS=1` for `claude` unless it is already set; raw `acpx` calls must set it too. Keep the executor's user-level Claude settings free of hooks, plugins, or a global `CLAUDE.md` that would make the worker orchestrate. |
| `grok` | `grok` (`grok agent stdio`) | `reasoning_effort` | Supports `--model` and `reasoning_effort` (`low`/`medium`/`high`/`xhigh`). Configure directly as `["grok", "agent", "stdio"]` in `~/.acpx/config.json` (do not wrap in `env ...`, which breaks `acpx`'s built-in Grok auth detection). |
| `agy` | `agy` (`agy acp` or built-in `antigravity`) | `thought_level` | Model fixed by agy's own settings; omit `--model`. `thought_level` (`low`/`medium`/`high`/`xhigh`) is advertised by the adapter; usually leave the default. |

## Permissions

`scripts/acpx-dispatch` applies everything in this section; the raw commands below
are the fallback when the script is unavailable. Always place global flags before
`<worker>`, pass `--format json` (needed to read `stopReason` and to detect failures
that print an error yet exit `0` in text mode), `--suppress-reads` (display-only
filter), an explicit `--timeout` (`1800` by convention; otherwise `acpx` reads config
`timeout` or applies none), and `--ttl 3600` on persistent sessions (the default
`300` lets the backend process exit while the orchestrator is still reviewing, so a
revision may land on a fresh backend session without prior context).

Flags:

- **Isolated worktree (writable default)**:
  `--approve-all --non-interactive-permissions fail`
- **In-place (writable, serial only)**:
  `--approve-reads --non-interactive-permissions deny --no-terminal --no-fs --permission-policy '{"autoApprove":["read","search","edit","delete","move"],"defaultAction":"deny"}'`
  - Pass these exact flags on `sessions new`, the initial prompt, and every revision.
  - `--permission-policy` only governs `session/request_permission`; ACP
    `fs/write_text_file` and `terminal/create` follow the top-level permission mode,
    so `--no-fs` / `--no-terminal` route edits through the agent's own tools under
    the policy.
- **Read-only (`exec`)**:
  `--approve-reads --non-interactive-permissions deny --no-terminal --permission-policy '{"autoApprove":["read","search"],"defaultAction":"deny"}'`

**Adapter permission mode (required).** The flags above only govern ACP permission
callbacks. Adapters whose native tools run without asking ignore them: verified on
`acpx 0.22.0`, a read-only `exec` with only these flags still let `codex`, `claude`,
and `agy` write files. Also switch the adapter's own `mode` config option:

| Worker | Read-only | In-place | Verified behavior |
| --- | --- | --- | --- |
| `codex` | `mode=read-only` | adapter default (caveat) | Default `agent` mode writes without asking; `read-only` blocks writes. |
| `claude` | `mode=default` | `mode=default` | Default `auto` mode writes and runs shell without asking; `default` routes edits and shell through the policy (edits approved, shell denied in-place). Avoid `plan`: it ends turns with `ExitPlanMode` instead of the report. |
| `agy` | `mode=plan` | not supported | `default` writes without asking; `plan` blocks writes (it may write a plan file under `~/.gemini`). Use a worktree for writable tasks. |
| `grok` | — (no `mode` option) | adapter default (caveat) | Writes via ACP `fs/write_text_file`, which the read-only flags deny. |

Set the mode with `--config-option mode=<value>` on `exec`, or
`acpx --cwd <dir> --format json <worker> set mode <value> -s "$TASK"` after
`sessions new`. In-place caveat: for `codex` and `grok` the native write path may
bypass the policy; prefer a worktree when the boundary matters. Strict isolation of
adapter MCP tools still needs an OS sandbox.

Raw recipe (fallback):

```bash
# Writable worktree + persistent session
BASE=$(git -C "$REPO" rev-parse HEAD) &&
WT="$(cd "$(dirname "$REPO")" && pwd)/$(basename "$REPO")-wt/$TASK" &&
git -C "$REPO" worktree add -b "agent/$TASK" "$WT" "$BASE" &&
acpx --cwd "$WT" --format json --ttl 3600 [--model "<model>"] <worker> sessions new --name "$TASK" &&
acpx --cwd "$WT" --format json <worker> set <effort-key> <effort> -s "$TASK" &&
acpx --cwd "$WT" --format json --approve-all --non-interactive-permissions fail \
  --suppress-reads --timeout 1800 --ttl 3600 <worker> -s "$TASK" -f "$REPO/.git/orchestrate/$TASK.md" \
  > "/tmp/$TASK.events.jsonl"

# Read-only exec
acpx --cwd "$REPO" --format json --approve-reads --non-interactive-permissions deny \
  --no-terminal --permission-policy '{"autoApprove":["read","search"],"defaultAction":"deny"}' \
  --suppress-reads --timeout 1800 [--model "<model>"] <worker> exec \
  [--config-option mode=<read-only-mode>] [--config-option <effort-key>=<effort>] \
  -f "$REPO/.git/orchestrate/$TASK.md" > "/tmp/$TASK.events.jsonl"

# stopReason and final report (text after the last tool call)
jq -rR 'fromjson? | .result.stopReason? // empty' "/tmp/$TASK.events.jsonl" | tail -1
jq -rjRn '[inputs | fromjson?] | (map(.params.update.sessionUpdate? // "" | test("^tool_call")) | rindex(true) // -1) as $i
  | .[$i+1:] | map(select(.params.update.sessionUpdate? == "agent_message_chunk") | .params.update.content.text? // "") | join("")' \
  "/tmp/$TASK.events.jsonl"
```

With `--format json`, a rejected `--model` on `sessions new` or an invalid `set` value
exits `1`; still confirm `"action":"session_ensured"` / `"action":"config_set"` in the
output before sending the prompt (text mode prints the error but exits `0`).

## Tiers

Default effort mapping per tier and worker (leave `--model` omitted unless overridden
by the user's global or repository model table, and defer to actual `configOptions`
advertised by the adapter/model):

| Worker | `hard` | `complex` | `simple` |
| --- | --- | --- | --- |
| `codex` | `xhigh` | `high` | `medium` |
| `claude` | — | `high` | adapter default |
| `grok` | `high` | `high` | adapter default |

`codex` at `hard` tier is the second brain (read-only cross-checks); `complex`
handles both medium and complex implementation.

How to pass model and effort in `acpx`:

- **Persistent session (writable tasks)**: pass `--model "<model>"` ONLY on
  `sessions new --name "$TASK"`, set effort with
  `acpx --cwd "$WT" <worker> set <effort-key> <effort> -s "$TASK"`, then send prompts
  with `-s "$TASK"` without re-passing `--model` (so `acpx` preserves
  `desired_config_options`). `acpx-dispatch --model/--effort` does this.
- **Stateless one-shot (`exec`, read-only tasks)**:
  `acpx ... [--model "<model>"] <worker> exec [--config-option <effort-key>=<effort>] -f "$REPO/.git/orchestrate/$TASK.md"`.

## Personal configuration

Register adapters in `~/.acpx/config.json`:

```json
{
  "agents": {
    "codex": { "argv": ["codex-acp"] },
    "claude": { "argv": ["claude-agent-acp"] },
    "grok": { "argv": ["grok", "agent", "stdio"] },
    "agy": { "argv": ["agy", "acp"] }
  }
}
```

Personal tier -> model ID mappings and role overrides belong in the user's own global
agent rules (for example `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`) or repository
instructions, which the orchestrator follows first. Example mapping using placeholders:

```markdown
- `orchestrate` 模型映射：
  - `codex`: hard=`<codex-strongest-model>` (reasoning_effort=medium), complex=`<codex-main-model>` (high), simple=`<codex-fast-model>` (medium)
  - `grok`: simple=`<grok-fast-model>`
  - `claude`: all=`<claude-api-model>` (high)
```
