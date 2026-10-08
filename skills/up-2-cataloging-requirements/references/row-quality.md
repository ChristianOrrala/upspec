# Row quality

Five checks for every row, with repairs. A row that fails one is repaired or
goes to the ledger; it does not stay as it is.

## The five checks

| Check | Fails | Passes |
|---|---|---|
| Measurable | "Search is fast." | "Search returns the first page within 2 seconds for 95 percent of requests at 100 concurrent users." |
| Singular | "Role: clerk; Need: import and export customers" | Two rows, one for import, one for export |
| Unambiguous | "The interface is user-friendly." | "A first-time customer completes a booking without help in a moderated test with 5 participants." |
| Testable | "The system is reliable." | "The service is available 99.5 percent of each calendar month between 07:00 and 20:00." |
| Unique | Two rows with the same identifier | Each identifier once |

## Words that hide a decision

normally, usually, quickly, fast, appropriate, adequate, sufficient,
reasonable, flexible, user-friendly, easy, intuitive, seamless, as needed, if
possible, etc., and so on, and/or, should, TBD.

Each one marks something nobody decided. Replace it with the decision, or keep
the row and open a ledger entry of kind Undecided. In a catalog, write
`<to be decided>` where the value will go; the check script accepts that marker
only together with a ledger, and reports it.

## Functional rows

- The role is specific. "User" is acceptable only when the product has one
  kind of user.
- The goal is something the role does with the system, in the role's words.
  "Create loan record" is the developer's phrase; "borrow a book" is the
  member's.
- Need is a short verb phrase, such as "borrow a book"; the role has its own cell.
- No screens, no buttons, no data fields. Those belong to the use case or to
  nothing at all.
- A statement of the form "the system must ..." with no role is usually a
  non-functional requirement, a constraint, or a business rule for one use
  case. Decide which.

## Non-functional rows

NFR and C rows use Statement and follow an EARS pattern from the conventions.
For example: `When a customer searches, the system shall return the first
page within 2 seconds for 95 percent of requests at 100 concurrent users`.
The number, unit and condition remain part of the NFR statement.

| Category | A threshold looks like | Usual verification |
|---|---|---|
| Performance | Time or throughput under a stated load | Load test |
| Scalability | A volume the system holds without changing the performance rows | Load test |
| Availability | Share of time, with the hours that count | Monitor |
| Security | Who may see or change what; what is recorded | Integration test, Inspection |
| Usability | An outcome for a kind of user in a kind of test; a named accessibility level | Inspection |
| Maintainability | A rule the code base keeps | Static rule |
| Portability | The environments it must run in | Integration test |

A row that cannot be checked by any method in the last column is not finished.
Say so in the ledger.

A non-functional requirement is written once, here. Use cases link it by
identifier on their `requirements` list and never repeat its text.

## Constraint rows

| Category | Example | Source column |
|---|---|---|
| Technical | The backend runs on the platform the organization already operates | Empty |
| Business | The first release fits the approved budget | Empty |
| Schedule | Production-ready before the season opens | Empty |
| Regulatory | Personal data is erased a fixed time after the last contact | Law or standard with article or section |
| Operational | Deployable by the existing operations team without new tooling | Empty, or the internal policy |

A regulatory row without a source cannot be reviewed by the person who knows
the regulation. Ask for the source; do not cite one from memory.

## What does not belong in the catalog

| Found in the material | Where it goes |
|---|---|
| A step-by-step description of a screen or interaction | The use case specification |
| A limit that applies to one behavior ("at most 5 open loans") | A business rule of that use case; note it for the specifier |
| The fields of a thing | The entity model |
| A technology preference that is not mandatory | The guideline file, or nowhere |
| A solution design | Nowhere yet |

## Updating a catalog

- Read first. Change only the rows the change touches.
- A dropped requirement keeps its row and identifier with Status `Rejected`
  (out of scope for good) or `Deferred` (later). Then list the use cases whose
  `requirements` list names it; they need attention.
- A changed requirement keeps its identifier. If the change is so large that
  the old intent is gone, reject the old row and add a new one.
- Progress Status is derived: Verified when every linking use case is Tested or
  Done, Implemented when every one is at least Implemented, In Progress when
  some are, Open otherwise.
