# Cross-file checks

Defects that only show when several files are read together. The lint finds
identical text and broken references; these need understanding. All findings
here are advisory.

## 1. Contradictions

**Where:** business rules of all use cases; a rule against the steps and flows
of its own use case; rules against the NFR and constraint rows.

Two statements contradict when no system can satisfy both for the same input:
different limits for the same quantity, a state one use case allows and
another forbids, a flow that ends where a rule says the use case continues.
Different rules for different actors or states are not a contradiction: check
the conditions first.

Report on the later of the two and name the other in qualified form
(`UC-009 BR-001`). Severity: warning. Do not pick a winner.

## 2. The same rule in other words

The lint catches identical text. You catch the paraphrase: same condition,
same consequence, different wording. The fix is to keep the rule in the use
case that owns the data and cite it from the other.

Severity: warning when the two wordings could be read differently, info when
they are equivalent.

## 3. Restated truth

| Copied into a use case | Owner |
|---|---|
| The attributes or format of a business noun | The entity model |
| A response time or another quality threshold | The NFR row |
| The look of a screen | A mockup |

Severity: info; warning when the copy already differs from the original.

## 4. Entity model consistency

Specifications name data in business words, so judge by meaning, not by
spelling: "the guest's email" matches `GUEST.email`.

Report:

- data a use case reads, shows or records that matches no entity or attribute;
- a rule that implies something the model contradicts (the rule says optional,
  the model says `Required`; the rule lists four states, the model three);
- a state move a flow performs that the entity's lifecycle does not allow;
- a relationship a flow relies on that the model does not have.

Skip when there is no entity model. Severity: warning.

## 5. Requirements that apply but are not linked

The lint checks that every listed id exists and that every functional
requirement is realized. It cannot tell that a use case forgot a quality
requirement or a constraint. Compare by topic: a response-time row and a use
case whose main step is a search; a data-protection constraint and a use case
that records personal data; an audit requirement and a use case that changes a
status.

This matters more than it looks: the implementer reads only the linked rows.
An unlinked constraint is an unseen constraint.

Severity: warning when the missing row sets a limit a test would check, info
otherwise.

## 6. Actors

Report:

- "System", or the system under design, as primary actor;
- primary actors joined by "or" or "and", or several primary actors who pursue
  different goals or need different scenarios (two use cases);
- a role or external system that acts in a step or flow but is declared
  neither primary nor secondary (an implementer may build it instead of
  integrating it): warning;
- an actor missing from the front matter despite acting in the scenario: warning.
  The overview is generated from front matter; stale output is `STALE_OVERVIEW`.

## 7. Across a journey test case

- A step whose test data cannot produce the state the next step needs.
- A journey that re-tests the detail of one use case instead of the seam
  between two.
- Placeholder data ("a valid customer") where a literal value belongs.
- A use case in the flow whose Status is still `Draft`: the journey rests on
  text that may change.

Severity: warning for the first and third, info for the others.

## Reporting

Each finding names both sides: the file and element where you report it, and
the element it conflicts with. One finding per defect, not one per file it
touches.
