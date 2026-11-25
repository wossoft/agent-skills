# Review and integration

Run every command in this file on the executor machine through the computer MCP's
`run_command` (`dir: "$REPO"`). `$WT`, `/tmp`, and the run artifacts exist only
there. Files in `$REPO` itself can also be read on the host through the shared mount.

## Review

1. Check the exit code (`0` done, `1` error, `2` bad args, `3` timeout,
   `4` no session, `5` permission denied, `6` read-only violation from
   `acpx-dispatch`, `130` interrupted), the `stopReason`, ACP errors/denials, and the
   worker's final report, all printed by `acpx-dispatch` (also in the run's
   `final.md` and `events-<n>.jsonl`). Do not rely on exit `0` alone: partial
   permission denials can still exit `0`, since exit `5` triggers only when all
   permission requests were denied/cancelled and zero approved. If you called
   `cancel`, wait for the turn to settle before reviewing. Inspect partial work
   before deciding anything; never auto-retry timeouts (`3`) or permission
   failures (`5`).
2. Read the actual git changes directly:
   - **Worktree run**: check status, stage intent-to-add so untracked text files
     appear in the diff, and verify the worker did not create commits on its own:
     ```bash
     git -C "$WT" status --short
     git -C "$WT" add -N . && git -C "$WT" diff HEAD
     git -C "$WT" rev-parse HEAD   # must still equal $BASE
     ```
     An unauthorized commit (`HEAD != $BASE`) is a violation to review carefully.
   - **In-place run**: compare against the pre-dispatch snapshot (`HEAD`, staged
     and unstaged diffs, plus hashes of untracked files in scope) — `git status --porcelain`
     alone cannot distinguish pre-existing user modifications from worker edits.
   - **Read-only (`exec`) run**: `acpx-dispatch` compares pre/post `git diff HEAD`
     plus untracked file hashes and exits `6` on any change (`git status --porcelain`
     alone misses re-edits to already-dirty files); any modification is a violation.
3. Check scope against the task: unexpected files, dependency or configuration
   changes, generated files edited by hand, removed user edits, or unauthorized commits.
4. Check acceptance criteria and real evidence: run project-appropriate checks in `"$WT"`
   (or `"$REPO"` for in-place) within authorization. Static checks do not prove
   runtime or visual behavior.
5. Decide `PASS`, `REVISION`, or `ESCALATE`. Request revisions for behavior,
   regression, security, scope, or failed required checks, not style preferences.

## Integrate a worktree run

Stage all changes (including new and binary files) inside `"$WT"`, write a binary
patch against `$BASE`, and apply to `"$REPO"` only after verifying clean application:

```bash
git -C "$WT" add -A &&
git -C "$WT" diff --cached --binary "$BASE" > "/tmp/$TASK.patch" &&
git -C "$REPO" apply --3way "/tmp/$TASK.patch"
```

Notes on `git apply --3way`: it implies `--index`, so it updates `"$REPO"`'s index,
errors if affected paths in `"$REPO"` already have staged vs working-tree mismatches,
and may leave 3-way conflict markers or unmerged index entries. Review the combined
diff and run the relevant checks in `"$REPO"` before cleanup.

Only AFTER patch generation, `git apply`, and checks in `"$REPO"` succeed, close
the ACP session BEFORE removing `"$WT"` (sessions are scoped by absolute `--cwd "$WT"`),
then remove the worktree and temporary branch:

```bash
acpx --cwd "$WT" <worker> sessions close "$TASK" &&
git -C "$REPO" worktree remove --force "$WT" &&
git -C "$REPO" branch -D "agent/$TASK"
```

If patch generation, `apply`, or checks fail (or the result is not integrated yet),
keep `"$WT"` and `"agent/$TASK"` intact and say so in the report.

Global maintenance (only with user authorization, never per-task): `acpx <worker> sessions prune`
matches closed records across **all repositories** for that adapter, not just
`"$REPO"`. Always preview with `--dry-run` first:
`acpx <worker> sessions prune --dry-run --older-than 14 --include-history`.

## Revision

Continue the existing worktree/checkout and named ACP session:

```bash
acpx-dispatch revise "$TASK" "$REPO/.git/orchestrate/$TASK-rev.md" --repo "$REPO"
```

It reuses the recorded worker, mode, absolute `--cwd`, and permission flags, does not
re-pass `--model`, and keeps `--ttl 3600`. Without the script, rerun the initial
prompt command from [routing.md](routing.md) with the same flags and `-s "$TASK"`.

Note that if the queue owner exited after idle TTL and the adapter cannot resume
or load the prior ACP session, `acpx` may create a fresh backend session under the
same local record. Revision prompts must still re-state scope, prohibitions, and
acceptance criteria (and include full handoff context if needed).

Start a new session/worktree only when the original run used `exec`, the session was
already closed, you are switching workers, or context has drifted (when starting
fresh on prior changes, reuse `"$WT"` or pass the prior patch). After two
unsuccessful attempts, close the session (`acpx --cwd "$WT" <worker> sessions close "$TASK"`)
and diagnose or implement on the host, or get a `codex` `hard`-tier read-only
second opinion via `acpx-dispatch run codex <task> <file> --mode read-only`.
