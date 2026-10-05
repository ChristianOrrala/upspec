# Change Log from the Baseline Review

Everything the review of the recovered specifications could not settle. Each
entry is decided by stakeholders and then handled like any other change,
specification first. Nothing here is fixed quietly.

A decision that leaves work is written `later` or `later: <the decision>`:
the entry is in the alignment backlog. A change that takes it up writes
`in change: <change record path>`; the audit's report closes it as
`aligned: <report path>` (one report per use case of the entry); a claim
not worth building is `dropped: <reason>`. With the A-files, `Ahead` names
the AHEAD item that carries the entry.

| # | Kind | Use case | What was found | Evidence | Sign-off test | Decision | Decided by | Ahead |
|---|------|----------|----------------|----------|---------------|----------|------------|-------|
| 1 | Undocumented behavior someone depends on | [UC-XXX] | [what the system does that nobody specified] | [ledger row] | [would the specification as recovered have been signed off?] | [specify and approve / later: specify it / dropped: why] | | |
| 2 | Behavior that stopped working | [UC-XXX] | [the validation that no longer fires, the flow that fails] | [ledger row] | | [later: what should happen] | | |
| 3 | Two paths doing the same job differently | [UC-XXX, UC-YYY] | [the two paths and how their rules differ] | [ledger rows] | | [later: which one is right; the other changes] | | |
| 4 | Claimed but not built | [UC-XXX or —] | [what the old document promises and the code does not do] | [old document path:line] | | [later / dropped: why] | | |
