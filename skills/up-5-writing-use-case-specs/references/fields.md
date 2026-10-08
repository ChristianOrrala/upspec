# Fields

What each part of the file means, what it becomes in code and tests, and the
defect that recurs in it.

## Contents

- Front matter fields
- Preconditions
- Main Success Scenario and Alternative Flows
- Postconditions
- Business Rules
- What is deliberately not a field

## Front matter fields

All keys below are required except `secondary_actors`. Values use the subset
in the conventions; no nested or multiline YAML. `requirements` and
`secondary_actors` are inline lists.

| Field | Rule | Becomes | Recurring defect |
|---|---|---|---|
| `id` | `UC-` and three digits, from the diagram | The identifier in file name, tests and code markers | Reusing the number of a removed use case |
| `name` | The goal as a short verb phrase, verbatim from the diagram | The file name, lowercased with hyphens | Paraphrasing the diagram's name |
| `primary_actor` | The role that pursues the goal. Several, comma-separated, only when each can start it alone for the same goal by the same scenario | Who may reach this behavior; which role tests act as | "System"; "Clerk or Manager"; two roles with different goals (that is two use cases) |
| `secondary_actors` | Roles and external systems the system calls upon. Omit the key when none | Things to integrate, not to build | Leaving out a system a step talks to: an agent may build it |
| `goal` | One sentence: the outcome and why | The sentence that disambiguates everything below | An action instead of an outcome ("Assign task"); "use the system" |
| `trigger` | The event that starts it: a request, a point in time, another system's message | The entry point | A state ("User is signed in"): that is a precondition. Test: *when does this happen?* An event has a moment |
| `status` | `Draft` when you write it | The gate for implementation | Setting `Approved` yourself |
| `requirements` | An inline list of catalog identifiers: at least one `FR`, plus every `NFR` and `C` that applies | The only requirement rows the implementer reads | Omitting an NFR or constraint that applies: the implementer never sees it |

## Preconditions

What is already true before the first step, established somewhere else
(usually by another use case), and never checked again inside this one.

Two tests:

1. The system can enforce it. "The member intends to return the book" is not a
   precondition.
2. Something established it. If nothing did, it is the trigger or a validation
   in the scenario.

Not a precondition: anything that depends on what the actor enters during the
use case. "A room is free for the requested dates" cannot be true before the
dates are entered; it is a validating step and a flow. Keep the stable state
underneath it ("The room inventory is set up").

Becomes: a guard in front of the behavior, not a validation with a message.

## Main Success Scenario and Alternative Flows

See the step and flow rules. The scenario is numbered from 1 without gaps and
contains only steps that succeed. Everything else is a flow.

## Postconditions

**Success postconditions:** the world when the goal is achieved. Name every
record created or changed.

**Failure postconditions:** the minimum that holds on *every* unsuccessful end,
whichever flow caused it: nothing half recorded, existing data unchanged, an
attempt that can be reconstructed if someone needs to. They are guarantees,
not reactions. "System shows an error message" is a step of a flow. A statement
true for one failure path only belongs in that flow.

Both lists are non-empty. If they are hard to write, the use case is still
unclear: fix that before writing steps.

Become: what is committed and what is rolled back, and the assertions at the
end of every test.

## Business Rules

| Rule | Why |
|---|---|
| `### BR-001: Name`, numbered per file from 001 | The use case is the namespace |
| Cited from the step or trigger that applies it | A rule nobody cites is not enforced anywhere |
| Cited from elsewhere as `UC-002 BR-004`, never copied | Copies drift |
| One decision per rule | Smaller rules give smaller changes later |
| Examples table under every rule, blank line before it, inputs then `result` | Fill each cell; quantified boundaries need rows on both sides |
| Stated so that a test can decide pass or fail | "Handles large volumes" cannot be tested |

A rule that applies to every use case of the project (for example how every
status change is recorded) is a requirement in the catalog, linked on the
`requirements` list. It is not copied into each file.

## What is deliberately not a field

| Classical field | Here |
|---|---|
| Scope and level | Always the system under design, always user-goal level |
| Stakeholders and interests | A thinking tool while writing postconditions; its results show up as validations and postconditions |
| Technology and data variations | Mechanism; left to the implementation |
| Priority | In the requirements catalog |
| Frequency, performance | Non-functional requirements |
| Open questions | Asked before writing, or reported in the hand-off; never a section of the file |
