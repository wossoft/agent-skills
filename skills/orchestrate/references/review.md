# Review and integration

## Review

1. Read `status`. `timeout`, `failed rc=N`, or `failed 无最终汇报` means execution
   failed; inspect partial work before deciding anything. Do not retry timeouts or
   permission failures automatically.
2. Read the actual changes: `changes.txt` and `patch.diff` for worktree runs; for
   in-place runs `changes.txt` is only `git status`, so diff the checkout against
   what was there before dispatch. A plan run that changed files is flagged in
   `changes.txt`; treat it as a violation.
3. Check scope against the task: unexpected files, dependency or configuration
   changes, generated files edited by hand, removed user edits, commits created by
   the worker ("警告：agent 擅自创建了提交").
4. Check acceptance criteria and real evidence: `check.log`, plus any missing checks
   you run yourself within authorization. Static checks do not prove runtime or
   visual behavior.
5. Decide PASS, REVISION, or ESCALATE. Request revisions for behavior, regression,
   security, scope, or failed required checks, not style preferences.

## Integrate a worktree run

```bash
git -C <repo> apply --3way <run>/patch.diff
```

`patch.diff` includes new files (the worktree was staged without committing). Apply
into the main checkout without discarding user changes; resolve conflicts, review
the combined diff, and run the relevant checks there. Then clean up:

```bash
git -C <repo> worktree remove --force <worktree> && git -C <repo> branch -D agent/<task>
```

Keep the worktree if the result is not integrated yet and say so in the report.

## Revision

Each run is a new conversation, so a revision prompt must be self-contained: the
original goal, scope, limits, acceptance criteria, the focused fix list, and the
prior run directory. Use a new task name. To build on the previous attempt, either
include the prior `patch.diff` path and let the worker apply it first, or run
`--in-place --repo <previous-worktree>`. After two unsuccessful attempts, diagnose
or implement on the host, or get a `--tier hard` second opinion.
