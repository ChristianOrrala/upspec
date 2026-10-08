---
outcome: [1 to 7, or migration]
element: [UC-XXX step N / UC-XXX A1 / UC-XXX BR-00N / no use case covers it]
decided_by: [Owner role; required for outcomes 2, 4, 5 and 6]
---
# Change record: [Short title]

## Context

[Who reported what, or the recovery change log entry it starts from.]

Sign-off test: [Would a stakeholder have signed off the specification as it stands, knowing what they want now? Yes or no, with the reason.]

## Decision

[The chosen outcome and the owner's decisions, each mapped to its specification element.]

| # | Decision | Decided by | Lives in |
|---|---|---|---|
| [1] | [What was decided] | [Owner role, date] | [UC-XXX BR-00N / UC-XXX step N / UC-XXX A1 / out of scope / open] |

## Specification change

[None, or what changes in which element. Name the Status reset without copying the use case's Status.]

## Consequences

[Differences from today and the impact. Omit a table when it does not apply.]

| Element | Today | After the change | Requested by | Seen in |
|---|---|---|---|---|
| [UC-XXX step N / UC-XXX A1 / UC-XXX BR-00N] | [Today's behavior] | [Changed behavior] | [Request or owner's decision] | [code / test <name> / observed] |

| Direction | Affected | What to do |
|---|---|---|
| Upward | [Requirement or scope] | [Action] |
| Sideways | [Use case citing the element] | [Action] |
| Downward | [Journey, tests, entity model] | [Action] |

[Next steps: pin rows seen only in code with passing tests and commit the pins before code changes. Then name the next skill and use case.]

<!-- Keep the following sections only when they apply. -->

## Sources of new behavior

| Element | Source |
|---|---|
| [UC-XXX A1 / UC-XXX BR-00N] | [the request / decision 1 / today / assumption 1] |

## Assumptions

| # | Assumption | Element |
|---|---|---|
| [1] | [What nobody decided, for the owner to confirm] | [UC-XXX BR-00N] |

## Reproduction

[For a defect: the failing test, named after the flow or rule, with literal data and expected outcome.]

## Urgent path

[For a hotfix: mitigation, who approved the specification edit, follow-up opened.]
