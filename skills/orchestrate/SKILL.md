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

Before dispatching API binding work, check the relevant repository conventions
and confirm the request, response (including pagination), and generated client
method and types where applicable. While a contract is unsettled, delegate
independent work such as routes or layouts if useful and defer API binding.

1. Pick a short slug without `/` for `$TASK` (for example `fix-paging`), and write
   the prompt to a file outside the repository (`/tmp/$TASK.md`), starting from
   [references/task-template.md](references/task-template.md). State goal,
   allowed files, contracts, relevant repository rules the worker may not load,
   prohibitions, and acceptance criteria, and keep the worker contract and required
   Chinese report structure (`## 改动文件`, `## 做了什么`, `## 没做什么`, `## 不确定 / 风险`)
   at the bottom.
2. Dispatch with this skill's `scripts/acpx-dispatch` (normally linked as
   `~/.local/bin/acpx-dispatch` via `acpx-dispatch --install`; `--help` for options).
   It wraps the `acpx` recipe in [references/routing.md](references/routing.md):
   creates the worktree and named session, passes `--model` only at creation, switches
   the adapter's own permission mode, sets effort, verifies each step from
   `--format json` output (rolling back the worktree if session creation fails), sends
   the prompt with `--ttl 3600`, and prints `stopReason`, ACP errors/denials, changed
   files, and the worker's final report. Choose model/effort per routing.md.
   ```bash
   # Writable (default): isolated worktree at HEAD + persistent session
   acpx-dispatch run <worker> "$TASK" "/tmp/$TASK.md" --repo "$REPO" [--model <m>] [--effort <e>]
   # Writable in-place (only when uncommitted changes are required; serial only)
   acpx-dispatch run <worker> "$TASK" "/tmp/$TASK.md" --repo "$REPO" --mode in-place
   # Read-only (diagnosis, review, research): stateless exec in adapter read-only mode
   acpx-dispatch run <worker> "$TASK" "/tmp/$TASK.md" --repo "$REPO" --mode read-only
   ```
   - The worktree sees only `HEAD`, not uncommitted changes, and does not sandbox
     external files or network. Never commit or stash user changes to make a worktree
     run possible; describe needed changes in the task file or use `--mode in-place`.
   - `--mode in-place` is refused for `agy`, whose native tools ignore the permission
     policy; for other adapters see the caveats in routing.md.
   - Read-only runs snapshot `git diff HEAD` plus untracked file hashes before and
     after, and exit `6` if anything changed. Exit `5` in read-only means every
     permission request was denied (for example a write or shell attempt); read the
     report before judging.
   - Artifacts live in `${TMPDIR:-/tmp}/acpx-dispatch/<repo>/<task>/`
     (`events-<n>.jsonl`, `final.md`, `stderr-<n>.log`, `meta.env`);
     `acpx-dispatch report "$TASK" --repo "$REPO"` reprints the latest round.
   - If the script is unavailable, run the raw `acpx` commands in routing.md.
3. Long runs & control:
   - Run `acpx-dispatch` with the host's background execution. For named sessions,
     monitor with `acpx --cwd "$WT" <worker> status -s "$TASK"` (`running` = healthy;
     `no-session` exits 0) or `acpx --cwd "$WT" --suppress-reads <worker> sessions watch -s "$TASK"`
     (stopping a watcher does not cancel the turn), or tail the run's `events-<n>.jsonl`.
   - Cancel an active named session cooperatively with
     `acpx --cwd "$WT" <worker> cancel -s "$TASK"` (`cancelled: false` exits 0 if
     nothing is active), and wait for the turn to settle before reviewing.
   - Exit codes follow `acpx`: `0` done, `1` error, `2` bad args, `3` timeout,
     `4` no session, `5` permission denied (only when all permission requests were
     denied and 0 approved), `130` interrupted; `acpx-dispatch` adds `6` for a
     read-only violation. Do not auto-retry `3` or `5`.

## Accept and integrate

Review the worker's diff and run the relevant project checks before deciding on
a revision. Apply small, low-risk fixes on the host when that is faster. Return
substantial gaps or regressions to the worker with the failed check or unmet
acceptance criterion.

Follow [references/review.md](references/review.md). Judge from exit code + `stopReason`
(printed by `acpx-dispatch`), actual git diffs/hashes, project checks, and the files themselves — never from the
worker's own summary. Exit `0` alone only means `acpx` finished (partial permission
denials can still exit `0`).

`$WT` and `$BASE` below are printed by `acpx-dispatch` and stored in the run's
`meta.env` (`CWD`, `BASE`).

- PASS: generate a `--binary` patch against `$BASE`, apply it to `"$REPO"`, and run
  checks in `"$REPO"`. Only after apply and checks succeed, close the ACP session
  (`acpx --cwd "$WT" <worker> sessions close "$TASK"`) BEFORE removing the worktree
  and branch (`git -C "$REPO" worktree remove --force "$WT" && git -C "$REPO" branch -D "agent/$TASK"`).
- REVISION: `acpx-dispatch revise "$TASK" "/tmp/$TASK-rev.md" --repo "$REPO"`
  continues the same worktree/checkout and named session with the same permission
  flags and no `--model`. Because a session can still be recreated if its backend
  process exited and the adapter cannot resume, re-state scope, prohibitions, and
  acceptance criteria in the revision prompt. Start a fresh task only when switching
  workers, after a read-only run or `close`, or to reset polluted context.
  After two failed revisions, stop redispatching; close the session and diagnose or
  implement on the host.
- Do not commit, push, or publish unless the user asked.

Report the outcome, the checks actually run, unverified runtime/browser/device
behavior, remaining risks, and which parts each agent did. If the orchestrator
wrote substantial code itself, say why it was not dispatched.
