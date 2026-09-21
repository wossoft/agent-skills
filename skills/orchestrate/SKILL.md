---
name: orchestrate
description: >
  Coordinate bounded implementation tasks using task specs, optional CLI workers,
  and host review. Use when the user requests orchestration or delegation of a
  substantial implementation. Ordinary edits, diagnosis, and code review do not
  require this workflow.
---

# Orchestrate

External workers require Bash, Python 3, a POSIX host, and the selected CLI on PATH.
Worktrees require Git.

Use this workflow for the current task only. Do not install global identity rules
or treat skill installation as authorization to dispatch every future request.
The host owns scope, integration, and acceptance.

## Decide whether to delegate

Handle small edits, requirement discovery, architecture decisions, and debugging
that depends on ongoing observations directly. Delegate when a substantial,
bounded task can be specified without losing essential conversation context.
Default to one task at a time; avoid making task files for work done directly.

Prefer native subagents when available, authorized, and sufficient for the task.
Use an external CLI when a different product, model, or tool environment provides
concrete value. Workers do not automatically inherit the conversation or the
host's authorization boundaries.

Choose by capability, availability, and user preference. Claude for backend work
and agy for UI are optional starting preferences, not requirements. Codex and Grok
can also implement tasks. Use an independent second opinion only when useful.
If no suitable worker is available, implement on the host. Do not install tools or
change credentials just to satisfy a routing preference.

## Prepare a task

For external workers, use this skill's `scripts/agent-run` (or a verified installed
link). Create a spec with `agent-run init-task <slug> --cwd <repo-root>` and fill
[references/task-template.md](references/task-template.md). Record the goal,
allowed files, relevant repository instructions, API contracts, existing changes,
authorization limits, acceptance criteria, and exact verification commands.
Verification follows the user's instructions and change risk as well as repository
rules; absence of a repository checklist does not mean no checks are needed.

Inspect the current checkout before dispatch. Keep work depending on uncommitted
changes in that checkout, serially. The runner records Git evidence before and
after; it does not isolate ordinary execution or restore overwritten changes.

## Execute

```bash
agent-run claude /absolute/path/TASK.md --cwd /absolute/path/repo
agent-run agy /absolute/path/TASK.md --cwd /absolute/path/repo --timeout 1200
```

The runner preserves permission controls; it has no permission-bypass switch.
Permission failures are blockers to report or handle within existing authority.
The timeout kills the worker process group and returns 124. No automatic retry:
inspect partial changes first. A zero exit code is only a process result.

Parallelize only independent tasks with stable interfaces and distinct file
ownership. For concurrent CLI implementation in the same repository, use separate
`--worktree` runs. These require a clean checkout and start at HEAD. Ignored files,
dependencies, and local configuration are not copied; describe any necessary setup
in the task. Do not commit or stash user changes to satisfy this prerequisite.

## Review, revise, integrate

Follow [references/review.md](references/review.md). Inspect actual changes and
verification evidence before PASS. For isolated work, integrate the reviewed
changes and verify the resulting target checkout before declaring completion.

Every CLI invocation starts a fresh conversation. A revision task must include the
original task and acceptance criteria, focused feedback, previous run artifacts,
and the existing execution directory. Use `--cwd <previous-worktree>` without
`--worktree` to revise in place. After two unsuccessful attempts, stop redispatching
and diagnose or implement on the host; ask only for a necessary user decision or
new authority.

Report the outcome, meaningful checks, unresolved risks, and any work still waiting
for integration. Mention executor details only when they help explain the result.
