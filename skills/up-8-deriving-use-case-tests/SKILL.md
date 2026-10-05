---
name: up-8-deriving-use-case-tests
description: >-
  Derives and maintains the tests of one use case from its specification, in any stack: lists the
  coverage units (main success scenario, each alternative flow, each business rule with its
  boundaries, success postconditions, failure guarantees, guarded preconditions, linked testable
  NFRs), picks the test layer from the use case's interface, writes one traceable test per unit
  asserting postconditions rather than internals, proves each rule test fails against a deliberately
  broken rule, and on a specification change updates, deletes or keeps tests according to the
  difference. Use when the user asks to write, generate, update or review tests for UC-XXX, asks which
  tests a use case needs, wants spec-based acceptance tests, asks whether the tests really guard a
  business rule, or suspects generated tests assert the wrong thing. Not for end-to-end journeys
  across several use cases and not for test-first design of code that has no use case.
---

# Deriving use case tests

Write and maintain the tests of one use case from its specification. Tests are
not invented next to the specification; they are the same contract seen from
the verifying side. They are also what makes change safe: when another use
case is synchronized, these tests are the firewall around this one.

A generated test can look right and guard nothing. This skill's job is tests
that provably fail when the behavior is broken.

This skill is stack-neutral. The project's test framework and its conventions
come from the project. Shared identifiers and markers:
[references/conventions.md](references/conventions.md).

## The unit list is the test plan

```bash
python3 scripts/coverage_units.py UC-006 --tests <test folder>
```

The script is in this skill's folder; use the base directory shown when the skill
was loaded, and do not search the disk for it. It lists every unit of the
use case and, where tests already exist, which tests carry each unit's label.

| Unit | Source | A test must |
|---|---|---|
| `Main` | Main success scenario | Run it end to end and assert every success postcondition |
| `A1`, `A2`, ... | Each alternative flow | Establish the trigger deliberately and assert the flow's outcome and where it leaves the use case |
| `BR-001`, ... | Each business rule | Assert the allowed side and the refused side, at the boundary |
| `Post-S-n` | Success postconditions | Be asserted by the `Main` test |
| `Post-F-n` | Failure postconditions | Be asserted by every test of a flow that ends: the state is what it was before |
| `Pre-n` | Preconditions | Be set up explicitly; one test shows the behavior cannot be entered without it |
| `NFR-...`, `C-...` | Linked rows with a threshold a test can observe | Be asserted where observable; otherwise say it is not measured here |

One test per unit at least. A test may cover a flow and the rule behind it;
then it names both.

## What to assert

- **Postconditions, not messages alone.** A test that checks only that a
  message appeared passes when the data is wrong. Assert the final state.
- **Failure guarantees.** For every flow ending in "Use case ends.": nothing
  was recorded, nothing changed. This is the assertion most often missing.
- **Boundaries.** A rule's `Examples:` line gives the values: just inside,
  just outside. Test both. If the rule has a quantity and no examples, that is
  a gap in the specification: say so, do not pick the boundary yourself.
- **Observable behavior only.** Never assert that a method was called, a query
  ran, or an internal structure has a shape. Such tests break on every
  refactoring and prove nothing about the contract.
- **Content the specification names.** If a step says the confirmation shows
  the work order number and the day, assert both.
- **Sameness exactly.** When a rule says two cases get the same answer (an
  unknown address and a failed lookup look alike), produce both and assert
  they are equal, whole. A check that each contains a phrase passes when one
  carries an extra sentence that tells them apart.

## Setup

Create exactly the state the preconditions and the flow's trigger require,
with literal values, inside the test. Nothing more. A test that passes only
because of data left by another test is a defect; so is setup that quietly
establishes more than the specification assumes.

## Which layer

Choose per use case, from how it is reached:

| The use case has | Primary test | Add |
|---|---|---|
| A user interface | The level that drives the interface without a real browser, if the stack offers one; it covers the full flow down to stored state | Fast tests of each rule in isolation |
| No interface: an API, a job, a consumer | An integration test against real dependencies | Fast tests of each rule in isolation |
| Behavior that exists only in a real browser (rendering, keyboard, downloads) | A browser test, for that behavior only | — |

Test-first fits rules, services and interfaces between systems: write the
failing test from the rule, then the code. For a user interface, specify,
build, then test. More in [references/layers.md](references/layers.md).

## Names and markers

- The suite carries the use case id and name: `UC006ViewTeamTasksTest`,
  `describe("UC-006: View Team Tasks")`.
- Each test names its unit: `main`, `a1`, `br001` in the test name, or the
  framework's annotation or tag.
- Identifiers have three digits.
- Follow the convention the project's existing tests use. If the project has
  none, use the test name.

Before writing, read two or three existing tests and the framework's current
documentation. Do not write framework calls from memory.

## Workflow

1. Read the specification and the rows on its Requirements line. If Status is
   below `Approved`, say so and ask before writing tests against text that may
   still change.
2. Run `coverage_units.py`. Existing tests for this use case are reconciled,
   never duplicated in a second suite.
3. Choose the layer.
4. Write or update one test per unit, with markers.
5. Run the suite. Report failures as they are; a failing test of correct code
   means the test or the specification is wrong, so find out which.
6. Run the guard check for every rule test and every flow test with
   `scripts/guard_check.py`, which breaks, tests, restores and logs:
   [references/guard-check.md](references/guard-check.md). A test that still passes when its
   rule is broken is not a test of that rule. Note which assertion caught each
   break; an assertion no break can make fail checks nothing.
7. Review each new or changed test with the three questions below.
8. Report with [templates/unit-to-test.md](templates/unit-to-test.md) and hand off to
   `up-9-auditing-spec-coverage`. Do not move Status yourself.

## When the specification changed

When asked to pin today's behavior before a change, write tests that pass
against the code as it is, and enter each test's name in the change record's
Seen in column (`test <name>`) for the row it pins. A test that replaces an
outside service with a stand-in pins our side only; where the row depends on
the service's answer, say so and leave the row to be observed on the real
service.

Take the change list (from `up-7-implementing-use-cases`, or compare the two
versions) and classify every existing test:

| The unit | The test |
|---|---|
| Changed | Update it to the new expectation |
| Removed from the specification | Delete it |
| Unchanged | Leave it untouched; it must stay green |
| New | Write it |

Re-review every test you touched, not only the new ones. A small wording
change in a rule can leave a test that looks the same and asserts the wrong
thing. Report all four groups, the empty ones too (`Deleted: none`): the
owner learns from the report that nothing else moved.

## Validation: three questions per test

1. Does the assertion match the postcondition or rule in the specification?
2. Does the setup establish only the stated preconditions and trigger?
3. Does the test fail when the rule is broken? (The guard check answers this.)

Then for the suite: every unit has a test or a stated reason; the working tree
is clean after the guard checks; no test asserts mechanism.

A human still reviews the tests. You can derive and check them; whether they
express what the business meant is not yours to certify.

## Worked example

`UC-001 Book Repair`: seven steps, flows A1 (no free slot, continues at step
3) and A2 (bike has an open work order, ends), rules BR-001 (at most 8 work
orders per day; examples 7 and 8) and BR-002 (one open work order per bike).

| Unit | Test | Asserts |
|---|---|---|
| Main | `main_books_work_order` | Work order exists with status Booked for bike, problem, day; free slots on that day reduced by one; confirmation names number and day |
| A1 | `a1_no_free_slot_offers_other_days` | Refusal names the days that still have slots; no work order recorded; a second choice then succeeds (continues at step 3) |
| A2 | `a2_open_work_order_ends` | Refusal names the open work order's number and status; **no work order recorded, free slots unchanged** |
| BR-001 | `br001_capacity_boundary` | With 7 on the day booking succeeds; with 8 it is refused |
| BR-002 | `br002_collected_does_not_block` | Last work order Completed: refused. Last work order Collected: accepted |
| Pre-1 | `pre1_requires_signed_in_customer` | The behavior cannot be reached without a signed-in customer |
| NFR-001 | — | Response time: not measured here; needs the load test named in the catalog |

Guard check for BR-001: with the capacity check disabled,
`br001_capacity_boundary` and `a1_no_free_slot_offers_other_days` fail, as
they should; code restored, tree clean.
