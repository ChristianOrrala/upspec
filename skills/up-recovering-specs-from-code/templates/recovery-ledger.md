# Recovery Ledger

Where every recovered element came from. Specifications carry no code
vocabulary; this file carries the link to the code instead.

Element is a use case (`UC-001`), a flow (`UC-001 A1`), a rule
(`UC-001 BR-002`) or an entity (`ENTITY CUSTOMER`). Evidence is one or more
`path:line` locations, separated by semicolons, relative to the repository
root. State is `recovered`, `verified` (a second reader checked the claim
against its evidence), `suspect` or `discarded`; the last two need a note, and
a suspect's note names its entry in the suspect list (`S-012`), which the
specification also names where it describes that behavior. A limit of
the implementation (a timeout, a retry count) is a note on the row of the rule
or flow it affects. Write no counts here: the ledger check prints them.

| Element | Evidence | State | Note |
|---|---|---|---|
| UC-001 | [path:line; path:line] | recovered | [entry points grouped under this goal] |
| UC-001 A1 | [path:line] | recovered | |
| UC-001 BR-001 | [path:line] | recovered | |
| UC-001 BR-002 | [path:line] | suspect | [S-001: bypassed by a second entry point, a leftover constant, unreachable ...] |
| ENTITY CUSTOMER | [path:line] | recovered | |
| ENTITY CUSTOMER required | [schema path:line; schema path:line] | recovered | [the required attributes, each with its schema line] |
| ENTITY ORDER lifecycle | [path:line where each state is written] | recovered | [states; a state nothing writes is a suspect] |
| [a guard not written into any specification] | [path:line] | discarded | [why it is accidental] |
