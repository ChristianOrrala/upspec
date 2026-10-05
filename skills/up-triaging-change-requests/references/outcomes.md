# The seven outcomes

What each classification means, how to recognize it, and what happens next.

## Contents

- Before classifying
- 1. Code wrong
- 2. Specification wrong
- 3. Test wrong
- 4. Specification ambiguous
- 5. Enhancement
- 6. New use case
- 7. No behavior change
- Borderline cases
- What changes downstream

## Before classifying

Restate the report as: actor, what they did, what happened, what they
expected. Then find the element: the step where it happened, the flow that
should have applied, the rule that decides. A report you cannot attach to an
element is about behavior the specifications do not describe.

## 1. Code wrong

The specification is clear, a stakeholder would sign it today, and the system
does something else.

- **Recognize:** you can point to the step, flow or rule and to a boundary
  example that the system violates.
- **Edit:** nothing in the specification. Confirming that it is right is the
  specification-first step.
- **Proof:** a failing test named after the flow or rule (`a2_...`,
  `br005_...`). If the unit's existing test passes although the behavior is
  wrong, the test is weak: that is a second finding for
  `up-8-deriving-use-case-tests`.
- **Then:** `up-7-implementing-use-cases` fixes the code. Status unchanged.

## 2. Specification wrong

The text says something nobody meant: a wrong number, a missing condition, a
flow that ends where it should continue. The code may faithfully implement the
wrong text.

- **Recognize:** the stakeholder reads the element and says "that was never
  right".
- **Edit:** the specification. Then code and tests follow.
- **Status:** back to `Reviewed`.

## 3. Test wrong

Specification and code agree. A test fails, or a tester objects, because the
test encodes another expectation.

- **Edit:** the test. Check why it was wrong: a test derived from an older
  version of the specification points to a synchronization that skipped the
  tests.

## 4. Specification ambiguous

Two careful readers take two meanings from the same sentence. The
implementation chose one; the reporter expected the other.

- **Recognize:** words that hide a decision (appropriately, normally, etc.), a
  quantity without boundary examples, "today" without a time zone, a step that
  does not say what is shown.
- **Edit:** the specification, after the owner chooses the meaning. Add the
  boundary example that would have prevented it.
- **Status:** back to `Reviewed`.
- **Value:** every later implementation benefits. Say this in the record; it
  is the outcome most worth the time.

## 5. Enhancement

The specification is right for what was wanted when it was approved. Now
something else is wanted: a changed rule, another field, a different flow.

- **Recognize:** the sign-off test answers yes.
- **Edit:** the specification. If the intent itself changes, the requirement
  row too (same identifier unless the old intent is gone). If it crosses the
  scope in the vision, the vision's Scope section first, by the owner.
- **Status:** back to `Reviewed`.

## 6. New use case

A goal no existing use case covers.

- **Check first** that it is not an alternative flow of an existing use case,
  that it is in scope, and that the system does not already do it. Behavior
  the code has without a specification is not new: write today's behavior
  first, then classify the request against it (SKILL.md, "When the system
  already does it").
- **Edit:** requirement row, diagram, a new specification. The new file starts
  as `Draft`.

## 7. No behavior change

Nothing a stakeholder could observe changes: refactoring, renaming inside the
code, a dependency update, a performance improvement that stays inside an
existing threshold, infrastructure and deployment.

- **Edit:** nothing in the specifications.
- **Say so:** the change carries the line `No behavior change: UC-012`, naming
  the use case whose code it touches (or `none` and the reason). That is what
  lets it pass a specification-first guard honestly.
- **Not this outcome** if a threshold in an NFR row changes, a message's
  content changes, an order of displayed items changes, or a limit changes.
  Those are observable.

## Borderline cases

| Report | Classification |
|---|---|
| "It is too slow." | An NFR threshold exists and is violated: 1. A threshold exists and is met: 5 (they want a stricter one). No threshold: 5, and the row is missing |
| "The message is unclear." | The specification states the message's content and the system shows it: 5. The specification says only "informs the customer": 4 |
| "It crashed." | A technical fault. If a failure postcondition was violated (half-recorded data), also 1. Root cause analysis is not this skill |
| "It works, but nobody asked for this." | Drift: code without specification. The owner decides: specify it (5) or remove it (1) |
| "The old system did it differently." | 5, unless the specification promised the old behavior |
| A security or data protection finding | Usually a missing constraint or rule: 5 with High priority, or 2 if a linked constraint was ignored (then 1) |

## What changes downstream

| Outcome | Requirement | Diagram | Specification | Entity model | Code | Use case tests | Journeys |
|---|---|---|---|---|---|---|---|
| 1 | — | — | — | — | fix | add the failing test | — |
| 2 | — | — | change | maybe | synchronize | update | check |
| 3 | — | — | — | — | — | fix | — |
| 4 | — | — | change | maybe | synchronize | update | check |
| 5 | maybe | — | change | maybe | synchronize | update | check |
| 6 | add | add | new | maybe | generate | new | maybe |
| 7 | — | — | — | — | change | untouched, green | — |

"Check" means: run the impact list; a journey that includes the use case may
carry test data the change invalidates.
