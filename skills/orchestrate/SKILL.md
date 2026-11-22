---
name: orchestrate
description: >
  Act as the orchestrator when the main agent (Claude Code, Codex, Grok, or another
  host) faces non-trivial work: decide what to do itself and what to dispatch to
  other ACP coding agents (Codex, Claude, cc-api, Grok, Antigravity) by role and
  difficulty, dispatch them directly through acpx (Agent Client Protocol), and verify
  results before integrating. Use for implementation, refactoring, diagnosis, research,
  or bulk chores; the default is to dispatch and spread work across workers rather than
  implement on the host. Also use whenever the user asks to delegate, parallelize,
  or get a second opinion. Skip for one- or two-line edits and pure Q&A.
---

# Orchestrate

The current main agent is the orchestrator. It owns scope, architecture decisions,
integration, final verification, and the report. Workers run directly through the
**Agent Client Protocol (ACP)** via `acpx`: writable tasks use an isolated
`git worktree` with a named persistent `acpx` session (`sessions new`), while
read-only tasks use stateless `acpx exec`. Each new task starts fresh and sees
only its task file.

## Roles

The orchestrator plans, decides, reviews, and integrates; workers implement. Default
to dispatch: the question is not "should I hand this off?" but "which worker gets
it?". The orchestrator keeps only:

- Scoping, decomposition, architecture decisions, and the interface contracts it
  writes into task files.
- Review, integration, final checks, and the report.
- Edits faster to make than to describe: one file, roughly 20 changed lines or
  fewer, intent fully clear.
- Work that depends on conversation context that cannot be written into a task
  file, and fixes after two failed revisions.

Everything else goes to a worker, including core logic, UI, and docs. The
orchestrator owns their design and acceptance, not their typing. Before editing
code yourself, check the list above; if the edit is not on it, write a task file.

Route by strength (`acpx` adapters, permissions, tiers, and personal overrides in
[references/routing.md](references/routing.md)):

| Worker | Give it |
| --- | --- |
| `codex` | Medium and complex reasoning-heavy code at the default `complex` tier: backend, APIs, databases, migrations, core business logic, complex refactors, root-cause diagnosis, tests that protect business rules. `hard` tier is the second brain: a read-only second opinion, architecture cross-check, or plan review (via read-only `exec`), not an implementer. |
| `cc-api` | Medium-complexity Claude-style work on a separate quota at the default `complex` tier: frontend and UI components, docs, README, reports, skills and prompts, copy, scoped implementation. Do not give it hard tasks or `hard` tier. |
| `grok` | Medium-complexity implementation at the default `complex` tier, plus fast work with live web and X context: bulk mechanical edits, renames, wiring, fixtures, i18n strings, config housekeeping, dependency and version checks and bumps, small scripts (`simple` tier), current package or API facts, summaries of logs and files. Also a parallel read-only reviewer. |
| `agy` | Web research, visual/design review, document and media conversion. |
| `claude` | Frontend or docs when the orchestrator is not Claude. |

Spread the load:

- Do not funnel everything to Codex. Give Codex the complex, reasoning-heavy part
  and send the medium, mechanical, UI, and docs parts of the same task to `grok`
  and `cc-api` in parallel, each with distinct file ownership and the shared contract in its task
  file. Example: a feature becomes `codex` backend + `cc-api` frontend + `grok`
  wiring, fixtures, and strings.
- When the preferred worker is already busy and the task fits another, give it to
  an idle worker instead of queueing.
- For hard diagnosis or review, run two read-only workers in parallel (for example
  `codex` at `hard` tier and `grok`, both via read-only `exec`) and compare their findings.
- Chore task files can be a few lines. Template overhead is not a reason to take
  work back.

Rules that apply to every host:

- Do not dispatch to your own product at the same tier just to offload work.
  Dispatching to yourself at a different tier (for example Codex host asking
  `codex` at `hard` tier for a second opinion) is fine. `cc-api` runs a separate
  config and quota, so a Claude host should use it for UI and docs; it is not
  self-dispatch.
- Dispatch without asking when the task falls in a role above. Dispatch independent
  subtasks in the same turn.
- If a worker ACP adapter/CLI is unavailable or failing, fall back to another worker
  that fits, then to yourself. Do not install tools or change credentials to satisfy
  routing.
- Workers never re-delegate. Every task file must include the worker contract from
  [references/task-template.md](references/task-template.md) explicitly prohibiting
  `acpx` / `orchestrate` calls.

## Dispatch

1. Write the prompt to a file outside the repository (for example `/tmp/<task>.md`),
   starting from [references/task-template.md](references/task-template.md). State goal,
   allowed files, contracts, relevant repository rules the worker may not load,
   prohibitions, and acceptance criteria, and keep the worker contract and required
   Chinese report structure (`## 改动文件`, `## 做了什么`, `## 没做什么`, `## 不确定 / 风险`)
   at the bottom.
2. Choose execution mode and model/effort per [references/routing.md](references/routing.md),
   and keep one quoted absolute working path (`"$WT"` or `"$REPO"`) consistent across
   session creation, `set`, prompts, `status`, `cancel`, and `sessions close`:
   - **Writable (default — isolated worktree + persistent session)**:
     ```bash
     BASE=$(git -C "$REPO" rev-parse HEAD) &&
     WT="$(cd "$(dirname "$REPO")" && pwd)/$(basename "$REPO")-wt/$TASK" &&
     git -C "$REPO" worktree add -b "agent/$TASK" "$WT" "$BASE" &&
     acpx --cwd "$WT" [--model "<model>"] <worker> sessions new --name "$TASK" &&
     # optional when setting non-default effort (omit for agy):
     acpx --cwd "$WT" <worker> set <effort-key> <effort> -s "$TASK" &&
     acpx --cwd "$WT" --approve-all --non-interactive-permissions fail \
       --suppress-reads --timeout 1800 <worker> -s "$TASK" -f "/tmp/$TASK.md"
     ```
     - Use `sessions new` (not `sessions ensure`) for fresh tasks so a reused task
       name never inherits stale context.
     - Pass `--model` ONLY on `sessions new`, never on `set` or `prompt`, so `acpx`
       preserves `desired_config_options`. Do not rely on `&&` / exit code alone for
       `sessions new` or `set`: in `acpx 0.22.0`, an unsupported `--model` on
       `sessions new` (leaving no session created) and an invalid `set` option both
       exit `0` after printing an error. Verify stdout (`created session` / session
       UUID for `sessions new`; `config set:` for `set`) before sending the prompt.
     - A worktree isolates only the Git checkout from `$BASE`; it does not see
       uncommitted changes and does not sandbox external files or network. Never commit
       or stash user changes to make a worktree run possible. Also check whether the
       target checkout contains `.acpxrc.json`, which overrides adapter/MCP config.
   - **Writable in-place (only when uncommitted checkout changes are required; run serially)**:
     Use only when the adapter constrains writes appropriately under policy (see
     [references/routing.md](references/routing.md) for caveats). Snapshot pre-dispatch
     state beyond `git status --porcelain` (`HEAD`, staged/unstaged diffs, and
     hashes of untracked files in scope), and pass the exact same permission flags on
     `sessions new`, initial prompt, and any revisions using a fresh unique `$TASK`:
     ```bash
     acpx --cwd "$REPO" --approve-reads --non-interactive-permissions deny \
       --no-terminal --no-fs \
       --permission-policy '{"autoApprove":["read","search","edit","delete","move"],"defaultAction":"deny"}' \
       [--model "<model>"] <worker> sessions new --name "$TASK" &&
     # optional when setting non-default effort (omit for agy):
     acpx --cwd "$REPO" <worker> set <effort-key> <effort> -s "$TASK" &&
     acpx --cwd "$REPO" --approve-reads --non-interactive-permissions deny \
       --no-terminal --no-fs \
       --permission-policy '{"autoApprove":["read","search","edit","delete","move"],"defaultAction":"deny"}' \
       --suppress-reads --timeout 1800 <worker> -s "$TASK" -f "/tmp/$TASK.md"
     ```
   - **Read-only (diagnosis, review, research — default stateless `acpx exec`)**:
     ```bash
     acpx --cwd "$REPO" --approve-reads --non-interactive-permissions deny \
       --no-terminal --permission-policy '{"autoApprove":["read","search"],"defaultAction":"deny"}' \
       --suppress-reads --timeout 1800 [--model "<model>"] \
       <worker> exec [--config-option <effort-key>=<effort>] -f "/tmp/$TASK.md"
     ```
     Compare pre/post snapshots (`git diff HEAD` plus untracked file hashes, not
     `git status --porcelain` alone) to verify no edits occurred. Note that
     `--no-terminal` and `--permission-policy` enforce ACP client callbacks only;
     strict read-only isolation for adapter-native tools/MCP requires an adapter
     read-only mode or OS sandbox. Use a named persistent session only when
     multi-turn investigation is explicitly needed.
3. Long runs & control:
   - Use the host's background execution for long runs. For named sessions, monitor
     with `acpx --cwd "$WT" <worker> status -s "$TASK"` (`running` = healthy background
     process; `no-session` exits 0) or `acpx --cwd "$WT" --suppress-reads <worker> sessions watch -s "$TASK"`
     (stopping a watcher does not cancel the turn). For `exec`, monitor via the host
     background task.
   - Cancel an active named session cooperatively with
     `acpx --cwd "$WT" <worker> cancel -s "$TASK"` (`cancelled: false` exits 0 if
     nothing is active), and wait for the turn to settle before reviewing.
   - `acpx` exit codes: `0` done, `1` error, `2` bad args, `3` timeout, `4` no session,
     `5` permission denied (only when all permission requests were denied and 0 approved),
     `130` interrupted. Do not auto-retry `3` or `5`.

## Accept and integrate

Follow [references/review.md](references/review.md). Judge from exit code + `stopReason`,
actual git diffs/hashes, project checks, and the files themselves — never from the
worker's own summary. Exit `0` alone only means `acpx` finished (partial permission
denials can still exit `0`).

- PASS: generate a `--binary` patch against `$BASE`, apply it to `"$REPO"`, and run
  checks in `"$REPO"`. Only after apply and checks succeed, close the ACP session
  (`acpx --cwd "$WT" <worker> sessions close "$TASK"`) BEFORE removing the worktree
  and branch (`git -C "$REPO" worktree remove --force "$WT" && git -C "$REPO" branch -D "agent/$TASK"`).
- REVISION: continue in the same worktree/checkout and named ACP session without
  re-passing `--model`, keeping the **same permission flags** as the initial run
  (`--approve-all --non-interactive-permissions fail` for worktree, or the full
  in-place permission flags for in-place). Because `acpx` may recreate the backend
  session if the queue owner exited and adapter resume fails, still re-state scope,
  prohibitions, and acceptance criteria in the revision prompt. Start a fresh session
  only when switching workers, after `exec` / `close`, or to reset polluted context.
  After two failed revisions, stop redispatching; close the session and diagnose or
  implement on the host.
- Do not commit, push, or publish unless the user asked.

Report the outcome, the checks actually run, unverified runtime/browser/device
behavior, remaining risks, and which parts each agent did. If the orchestrator
wrote substantial code itself, say why it was not dispatched.
