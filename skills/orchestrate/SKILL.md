---
name: orchestrate
description: >
  Make Claude the orchestrator for non-trivial work: Claude scopes, splits,
  dispatches, and verifies, while ACP coding agents (Codex, Claude Code in API
  mode, Grok, Antigravity) on an executor machine do the implementation. Workers
  run through acpx (Agent Client Protocol), reached via the computer MCP's
  run_command. Use for implementation, refactoring, diagnosis, research, or bulk
  chores; the default is to dispatch and spread work across workers rather than
  implement on the host. Also use whenever the user asks to delegate, parallelize,
  or get a second opinion. Skip for one- or two-line edits and pure Q&A.
---

# Orchestrate

Claude is the orchestrator. It owns scope, decomposition, architecture decisions,
dispatch, acceptance, integration, final verification, and the report. Workers are
ACP agents on the **executor machine**, driven through **`acpx`**. Writable tasks
run in an isolated `git worktree` with a named persistent `acpx` session
(`sessions new`), and read-only tasks use stateless `acpx exec`. Each new task
starts fresh and sees only its task file.

## Executor machine

`acpx`, `acpx-dispatch`, the worker CLIs, and the project toolchains live on the
executor, not on the host Claude runs on. Reach the executor with the computer MCP
tools: `run_command` and `command_job` (shown as `mcp__computer__*`; load them with
ToolSearch if they are deferred).

- **Shared repository.** Project folders are mounted on the host at the same
  absolute path as on the executor, so `$REPO` means the same files on both sides.
  Read and edit files in `$REPO` with the host's own file tools. Run every `git`,
  `acpx`, `acpx-dispatch`, and project check command on the executor through
  `run_command` with `dir: "$REPO"`. Git over the mount is slow and can see stale state.
- **Not shared.** Worktrees (`$REPO-wt/<task>`, a sibling of `$REPO`), the executor's
  `/tmp` and `$TMPDIR`, and the `acpx-dispatch` artifacts are only on the executor.
  Inspect them with `run_command`.
- **Task files** go in `$REPO/.git/orchestrate/<task>.md`. Git never tracks that
  path, and both sides can see it. Write the file with the host's Write tool and
  pass that absolute path to `acpx-dispatch`.
- **Long commands.** Start `acpx-dispatch run|revise` with `run_command`
  `background: true`. That allows up to 21600 seconds, while the foreground limit is
  1800. Keep the returned job id. Do other orchestration work in the meantime, such as
  dispatching more tasks or reviewing finished ones. Collect the result with
  `command_job` (`wait_seconds` up to 50), and use `stop: true` only to abandon a run.
  Short commands (`git diff`, `report`, `status`, checks under two minutes) run in
  the foreground.
- **Preflight** once per session:
  `command -v acpx acpx-dispatch jq git && acpx --version`. If `acpx-dispatch` is
  missing, call it by path from the executor's checkout of this skill. You can also
  ask the user before running `<skill-dir>/scripts/acpx-dispatch --install`. Never
  install tools or change credentials on the executor without asking.
- If the computer MCP is unavailable, stop and tell the user. Do not fall back to
  implementing everything on the host.

## Roles

Claude plans, decides, reviews, and integrates, and workers implement. Default to
dispatch. The question is not "should I hand this off?" but "which worker gets it?".
Claude keeps only:

- Scoping, decomposition, architecture decisions, and the interface contracts it
  writes into task files.
- Review, integration, final checks, and the report.
- Edits faster to make than to describe: one file, roughly 20 changed lines or
  fewer, intent fully clear.
- Work that depends on conversation context that cannot be written into a task
  file, and fixes after two failed revisions.

Everything else goes to a worker, including core logic, UI, and docs. Claude owns
their design and acceptance, not their typing. Before editing code yourself, check
the list above. If the edit is not on it, write a task file.

Route by strength. [references/routing.md](references/routing.md) has the `acpx`
adapters, permissions, tiers, and personal overrides.

| Worker | Give it |
| --- | --- |
| `codex` | Medium and complex reasoning-heavy code at the default `complex` tier: backend, APIs, databases, migrations, core business logic, complex refactors, root-cause diagnosis, and tests that protect business rules. At `hard` tier it is the second brain: a read-only second opinion, architecture cross-check, or plan review (via read-only `exec`), not an implementer. |
| `claude` | Claude Code in API mode on the executor, with its own config and quota. At the default `complex` tier: frontend and UI components, docs, README, reports, skills and prompts, copy, and scoped implementation. Do not give it hard tasks or `hard` tier. |
| `grok` | Medium-complexity implementation at the default `complex` tier, and fast work that needs live web and X context: bulk mechanical edits, renames, wiring, fixtures, i18n strings, config housekeeping, dependency and version checks and bumps, small scripts (`simple` tier), current package or API facts, and summaries of logs and files. It is also a parallel read-only reviewer. |
| `agy` | Web research, visual/design review, and document and media conversion. |

Spread the load:

- Do not funnel everything to Codex. Give Codex the complex, reasoning-heavy part.
  Send the medium, mechanical, UI, and docs parts of the same task to `grok` and
  `claude` in parallel. Give each one distinct file ownership and put the shared
  contract in every task file. Example: a feature becomes `codex` backend +
  `claude` frontend + `grok` wiring, fixtures, and strings.
- When the preferred worker is already busy and the task fits another, give it to
  an idle worker instead of queueing.
- For hard diagnosis or review, run two read-only workers in parallel (for example
  `codex` at `hard` tier and `grok`, both via read-only `exec`) and compare their
  findings.
- Chore task files can be a few lines. Template overhead is not a reason to take
  work back.

Rules:

- The `claude` worker is not self-dispatch. It runs on the executor with a separate
  API config and quota, so use it freely for UI and docs.
- Dispatch without asking when the task falls in a role above. Dispatch independent
  subtasks in the same turn, each as its own background job.
- If a worker's adapter or CLI is unavailable or failing, fall back to another
  worker that fits, and only then to yourself.
- Workers never re-delegate. Every task file must include the worker contract from
  [references/task-template.md](references/task-template.md), which explicitly
  prohibits `acpx` / `orchestrate` calls.

## Dispatch

Before dispatching API binding work, check the relevant repository conventions.
Confirm the request, the response (including pagination), and the generated client
method and types where applicable. While a contract is unsettled, you can still
delegate independent work such as routes or layouts, and defer API binding.

1. Pick a short slug without `/` for `$TASK` (for example `fix-paging`). Write the
   prompt to `$REPO/.git/orchestrate/$TASK.md`, starting from
   [references/task-template.md](references/task-template.md). State the goal, the
   allowed files, contracts, relevant repository rules the worker may not load,
   prohibitions, and acceptance criteria. Keep the worker contract and the required
   Chinese report structure (`## 改动文件`, `## 做了什么`, `## 没做什么`,
   `## 不确定 / 风险`) at the bottom.
2. Dispatch on the executor with `scripts/acpx-dispatch` (normally linked as
   `~/.local/bin/acpx-dispatch`; `--help` lists the options). Use `run_command`
   with `dir: "$REPO"` and `background: true`. The script wraps the `acpx` recipe in
   [references/routing.md](references/routing.md). It creates the worktree and named
   session, passes `--model` only at creation, switches the adapter's own permission
   mode, and sets effort. It verifies each step from `--format json` output and rolls
   back the worktree if session creation fails. Then it sends the prompt with
   `--ttl 3600`, and prints `stopReason`, ACP errors/denials, changed files, and the
   worker's final report. Choose model and effort per routing.md.
   ```bash
   T="$REPO/.git/orchestrate/$TASK.md"
   # Writable (default): isolated worktree at HEAD + persistent session
   acpx-dispatch run <worker> "$TASK" "$T" --repo "$REPO" [--model <m>] [--effort <e>]
   # Writable in-place (only when uncommitted changes are required; serial only)
   acpx-dispatch run <worker> "$TASK" "$T" --repo "$REPO" --mode in-place
   # Read-only (diagnosis, review, research): stateless exec in adapter read-only mode
   acpx-dispatch run <worker> "$TASK" "$T" --repo "$REPO" --mode read-only
   ```
   - The worktree sees only `HEAD`, not uncommitted changes. It does not sandbox
     external files or the network. Never commit or stash user changes to make a
     worktree run possible. Describe the needed changes in the task file or use
     `--mode in-place`.
   - `--mode in-place` is refused for `agy`, because its native tools ignore the
     permission policy. For other adapters, see the caveats in routing.md.
   - Read-only runs snapshot `git diff HEAD` plus untracked file hashes before and
     after, and exit `6` if anything changed. In read-only, exit `5` means every
     permission request was denied (for example a write or shell attempt). Read the
     report before judging.
   - Artifacts live on the executor in `${TMPDIR:-/tmp}/acpx-dispatch/<repo>/<task>/`
     (`events-<n>.jsonl`, `final.md`, `stderr-<n>.log`, `meta.env`).
     `acpx-dispatch report "$TASK" --repo "$REPO"` reprints the latest round.
   - If the script is unavailable, run the raw `acpx` commands in routing.md on the
     executor.
3. Long runs and control (all on the executor via `run_command`):
   - Poll the background job with `command_job`. For more detail on a named session,
     run `acpx --cwd "$WT" <worker> status -s "$TASK"` (`running` = healthy;
     `no-session` exits 0) or tail the run's `events-<n>.jsonl`.
   - Cancel an active named session cooperatively with
     `acpx --cwd "$WT" <worker> cancel -s "$TASK"` (`cancelled: false` exits 0 if
     nothing is active). Wait for the background job to finish before reviewing.
   - Exit codes follow `acpx`: `0` done, `1` error, `2` bad args, `3` timeout,
     `4` no session, `5` permission denied (only when all permission requests were
     denied and 0 approved), `130` interrupted. `acpx-dispatch` adds `6` for a
     read-only violation. Do not auto-retry `3` or `5`.

## Accept and integrate

Review the worker's diff and run the relevant project checks on the executor before
deciding on a revision. When it is faster, apply small, low-risk fixes yourself in
`$REPO` after integration. Return substantial gaps or regressions to the worker with
the failed check or unmet acceptance criterion.

Follow [references/review.md](references/review.md). Judge from the exit code and
`stopReason` (printed by `acpx-dispatch`), the actual git diffs and hashes, project
checks, and the files themselves. Never judge from the worker's own summary. Exit
`0` alone only means `acpx` finished, because partial permission denials can still
exit `0`.

`$WT` and `$BASE` below are printed by `acpx-dispatch` and stored in the run's
`meta.env` (`CWD`, `BASE`). `$WT` exists only on the executor.

- PASS: on the executor, generate a `--binary` patch against `$BASE`, apply it to
  `"$REPO"`, and run checks in `"$REPO"`. Only after the apply and checks succeed,
  close the ACP session (`acpx --cwd "$WT" <worker> sessions close "$TASK"`). Do this
  BEFORE removing the worktree and branch
  (`git -C "$REPO" worktree remove --force "$WT" && git -C "$REPO" branch -D "agent/$TASK"`).
- REVISION: write `$REPO/.git/orchestrate/$TASK-rev.md` and run
  `acpx-dispatch revise "$TASK" "$REPO/.git/orchestrate/$TASK-rev.md" --repo "$REPO"`
  in the background. It continues the same worktree or checkout and the same named
  session, with the same permission flags and no `--model`. A session can still be
  recreated if its backend process exited and the adapter cannot resume, so re-state
  the scope, prohibitions, and acceptance criteria in the revision prompt. Start a
  fresh task only when switching workers, after a read-only run or `close`, or to
  reset polluted context. After two failed revisions, stop redispatching: close the
  session and diagnose or implement on the host.
- Once a task is integrated or abandoned, delete its files in `.git/orchestrate/`.
- Do not commit, push, or publish unless the user asked.

Report the outcome, the checks actually run (and on which machine), unverified
runtime, browser, or device behavior, remaining risks, and which parts each agent
did. If Claude wrote substantial code itself, say why it was not dispatched.
