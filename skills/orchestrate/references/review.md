# Review and revision

1. Read the run report and worker summary. Nonzero exit means execution failed or
   timed out; zero does not prove acceptance. Inspect partial work before retrying.
2. Review in the report's `cwd`. Compare `before/` and `after/`: HEAD, status,
   staged and unstaged patches, and untracked manifests. Read new files directly.
   These are evidence, not a backup or automatic attribution system. Ignored files
   are excluded. If Git is unavailable, explicitly review relevant files using
   another baseline; do not imply Git coverage.
3. Preserve pre-existing changes. Investigate unexpected HEAD/index changes,
   removed user edits, dependencies, configuration, generated files, and excess
   scope against the original task. Do not revert unrelated changes.
4. Check observable acceptance criteria and actual verification evidence. Run
   necessary missing checks within authorization; report unavailable checks.
5. Decide PASS, REVISION, or ESCALATE. Request revisions for behavior, regression,
   security, scope, or required-check failures, not stylistic preference.

## Revision

Create a self-contained task with the original goal, scope, authorization limits,
acceptance criteria, and verification, then add a focused fix list and prior run
paths. The CLI starts a new session; selecting the same product does not resume it.
Use the previous execution directory. Do not add `--worktree` again.

After two unsuccessful attempts, diagnose or implement on the host, or obtain an
independent second opinion when justified. Do not automatically retry timeouts or
permission failures. Ask the user when a required decision or new authority is
missing.

## Worktree integration

The host integrates only reviewed changes, preserving target checkout changes.
Worker modifications normally remain uncommitted; do not assume cherry-pick is
available. Transfer the reviewed tracked changes and new files using a method that
preserves staged content and detects conflicts. Resolve conflicts, inspect the
combined diff, and run relevant checks in the target checkout before completion.
Do not commit or force-remove a worktree without authorization. Report retained
worktree paths; the runner intentionally does not delete them.
