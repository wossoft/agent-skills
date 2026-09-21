# Legacy identity rule

This file is retained to explain migration from the previous installation guide.
It is not an always-on rule and should not be copied to global rules directories.
Use `orchestrate` for a requested, bounded delegation task; ordinary work stays in
the current session.

If an earlier installation copied Session Lead rules into a host's global rules,
review and remove only that copied section with the user's authorization and a
recoverable backup. Updating this skill does not change those installed rules.
