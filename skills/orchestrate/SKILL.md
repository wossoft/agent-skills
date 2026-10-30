---
name: orchestrate
description: >
  Act as the orchestrator when the main agent (Claude Code, Codex, Grok, or another
  host) faces non-trivial work: decide what to do itself and what to dispatch to
  other CLI agents (Codex, Claude, cc-api, Grok, Antigravity) by role and difficulty,
  run them through agent-run, and verify results before integrating. Use for
  implementation, refactoring, diagnosis, research, or bulk chores that can be
  scoped and handed off, and whenever the user asks to delegate, parallelize, or get
  a second opinion. Skip for one- or two-line edits and pure Q&A.
---

# Orchestrate

The current main agent is the orchestrator. It owns scope, architecture decisions,
integration, final verification, and the report. Workers are disposable: each run is
a fresh conversation that sees only the task file.

## Roles

Route by role first, then by availability. Defaults (see
[references/routing.md](references/routing.md) for tiers and user overrides):

| Work | Default owner |
| --- | --- |
| Core logic, architecture decisions, UI/frontend, docs (README, technical docs, reports), integration and verification | Orchestrator itself |
| Backend: APIs, server code, databases, migrations; any well-scoped implementation, diagnosis, or refactor that can be done independently | `codex` (first choice) |
| Second opinion on very hard problems, deep diagnosis, architecture cross-check | `codex --tier hard` |
| Chores: bulk mechanical edits, lookups, small scripts, version checks, file housekeeping, simple summaries | `grok` or `cc-api` (after Codex in priority) |
| Web research, visual/design review, document and media conversion | `agy` |
| Frontend or docs work when the orchestrator is not Claude | `claude` |

Rules that apply to every host:

- Do not dispatch to your own product at the same tier just to offload work; doing
  it yourself is cheaper. Dispatching to yourself at a different tier (for example
  Codex host asking `codex --tier hard` for a second opinion) is fine.
- Dispatch without asking when the task falls in a role above. Dispatch independent
  subtasks in the same turn, each with distinct file ownership.
- Do trivial edits directly when dispatch clearly costs more than it saves, but do
  not use that as a reason to do everything yourself.
- If a worker CLI is unavailable or failing, fall back to the next owner or do it
  yourself. Do not install tools or change credentials to satisfy routing.
- Workers never re-delegate. agent-run refuses nested calls.

## Dispatch

Use this skill's `scripts/agent-run` (normally linked as `~/.local/bin/agent-run`;
`agent-run --help` for options).

1. Write the prompt to a file. Start from `agent-run template` (the same content as
   [references/task-template.md](references/task-template.md)). State goal, allowed
   files, contracts, relevant repository rules the worker may not load, prohibitions,
   and acceptance criteria. agent-run appends the worker contract and the report
   format (changed files / done / not done / uncertain).
2. Pick mode and tier:
   - Writable tasks use the default `--mode build`: an isolated worktree at HEAD with
     permission prompts skipped. It does not see uncommitted changes; if the task
     depends on them, describe them in the prompt or run serially with `--in-place`
     (permission controls stay on). Never commit or stash user changes to make a
     worktree run possible.
   - Read-only tasks (diagnosis, review, research) use `--mode plan` in the original
     checkout.
   - Choose `--tier` by difficulty: `hard` very hard, `complex` default, `simple`
     easy, `cu` computer use. Do not default to the highest tier.
   - Add `--check "<command>"` with the project-appropriate check for the change.
3. Run:

   ```bash
   agent-run codex api-pagination /path/to/prompt.md --repo /path/to/repo \
     --tier complex --check "dotnet build src/Api"
   ```

   For long runs use the host's background execution and watch
   `~/.agent-runs/<repo>/<task>/events.jsonl`; intervene on errors or long silence.
   `agent-run ls` lists runs. Exit codes: 0 done, 1 failed, 124 timeout, 2 bad args.

## Accept and integrate

Follow [references/review.md](references/review.md). Judge from `changes.txt`,
`patch.diff`, `check.log`, and the files themselves, never from the worker's own
summary. Exit 0 only means the process finished.

- PASS: apply the patch to the main checkout, preserving user changes, run the
  relevant checks there, then remove the worktree and branch.
- REVISION: a new run with the full original task, focused fixes, and prior artifact
  paths. After two failed attempts, stop redispatching; diagnose or implement on the
  host.
- Do not commit, push, or publish unless the user asked.

Report the outcome, the checks actually run, unverified runtime/browser/device
behavior, remaining risks, and which parts each agent did.
