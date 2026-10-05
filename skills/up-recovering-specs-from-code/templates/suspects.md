# Suspects

Behavior the recovery found that looks unintended, unreachable, bypassed or
contradictory. Nothing here was corrected: each specification describes the
system as it behaves today. Evidence is one or more `path:line` locations,
separated by semicolons, relative to the repository root.

Kind `decide` is a question about behavior: the owner settles it in the
baseline review. Kind `tidy` has no behavior question (a stale comment, dead
code, a document that disagrees with the code) and goes to whoever maintains
the code. One finding, one entry; the ledger row of a suspect names its id.

| Id | Kind | Use case | What the system does | Evidence | Question |
|---|---|---|---|---|---|
| S-001 | decide | [UC-XXX] | [what happens today, in business words] | [path:line] | [the question for the owner: is this wanted?] |
| S-002 | tidy | [UC-XXX] | [the stale comment, dead path or disagreeing document] | [path:line] | None |
