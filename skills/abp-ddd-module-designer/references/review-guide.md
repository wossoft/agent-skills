# Reviewing an ABP business module

Use the core rules in SKILL.md as the design baseline. This guide describes how to establish findings, not an additional architecture checklist.

## Trace the affected behavior

Start with the reported issue or requested use case. Follow its entry point through authorization, application orchestration, domain operations, persistence, and relevant event consumers.

Identify the actual invariant and every write path that could bypass it. Inspect relevant tests and configuration before inferring missing behavior from one file.

For concurrency-sensitive behavior, examine transaction scope, database constraints, and conflict handling. For external effects, inspect retry and failure handling when they affect the requested behavior.

## Separate defects from preferences

- Report a correctness issue when a concrete execution path can violate a requirement.
- Report a boundary issue with its actual consequence, such as domain code depending on persistence details or a write bypassing an invariant.
- Treat naming, folder layout, and alternative abstractions as optional improvements unless the repository requires them.
- Do not infer a defect solely from public setters, IQueryable, or a shared DbContext without examining their use and project conventions.
- If a requirement is unknown, state the uncertainty rather than inventing a business rule.

## Present actionable findings

For each material finding, provide the location, triggering condition, consequence, and smallest corrective action. Prioritize correctness and data integrity over style.

For a proposed fix, identify the narrow regression check that would demonstrate the issue is resolved. Mention migrations or caller changes only when required by the fix.

If no concrete issues are found, say so and state inspection limits. Do not fill a review with speculative refactors or an unsolicited module skeleton.
