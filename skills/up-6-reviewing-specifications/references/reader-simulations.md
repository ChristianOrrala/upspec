# Reader simulations

Part B of a review. Read the scope three times, each time with one question
and one output. Findings from any reading are `warning` when they will make
the implementation or the tests wrong, `info` otherwise.

## Contents

- Reading 1: the stakeholder
- Reading 2: the engineer
- Reading 3: the literal implementer
- The ten recurring mistakes, by reading
- What is not a finding

## Reading 1: the stakeholder

**Read only:** the front matter and the main success scenario. Skim, as a busy
person would.

**Answer in two sentences:**

1. What will I get?
2. How will I tell, on delivery, whether I got it?

**Findings:**

| Observation | Severity |
|---|---|
| You cannot answer question 1 from the goal and the last step | warning |
| The goal names an action ("assign task"), not an outcome | info |
| The use case is not a goal the primary actor would come for: a technical step, or a whole area of work that hands over to another role or waits for an outside event | warning; fixed by the use case map |
| You needed technical knowledge to follow a step | warning |
| The scenario is longer than nine steps or you lost the thread | info |
| A quantity a stakeholder must confirm is hidden in prose instead of a rule | info |
| The scenario does not start at the trigger or does not arrive at the goal | warning |

## Reading 2: the engineer

**Read:** the whole file, the rows on its `requirements` list, the entities it
names.

**Produce the test list.** One line per path: the main scenario, each
alternative flow. For each, write the observable end: a success postcondition,
a failure guarantee, or the step where the flow continues. Then one line per
business rule: which path exercises it, and what the boundary values are.

**Findings:**

| Observation | Severity |
|---|---|
| A step that can fail (a validation, a lookup, a payment, a call to another system, a change by someone else) with no flow anchored to it | warning |
| A path with no observable end | warning |
| A rule that no path reaches | warning |
| A rule a test cannot decide ("handles large volumes", "in time") | warning; suggest the measurable form |
| A rule with a quantity or date and no boundary stated | info |
| A failure postcondition that is a reaction, or true for one failure path only | warning |
| A flow that ends after leaving something the failure postconditions rule out | warning |
| A precondition that nothing establishes, or that depends on input given during the use case | warning |
| A trigger that is a state, or a precondition that is an event | warning |
| A scenario made of interactions only: no validation, no state change | warning |

Report a missing end or an unreached rule once per use case, not once per step.

## Reading 3: the literal implementer

**Read:** exactly what an implementing agent is given: the use case, the
linked requirement rows, the entity model. Nothing else, and no goodwill.

**Produce the invention list:** every decision you would have to make to build
this that these files do not make.

```text
UC-004 step 2   which details of the room are shown, in what order      behavior
UC-004 step 5   what the confirmation tells the guest                   behavior
UC-004 A1       whether the dates entered are kept for the retry        behavior
UC-004 step 4   how the availability is computed                        mechanism (not a finding)
UC-004 step 2   layout of the list                                      free
```

Tag each item:

| Tag | Meaning | Finding? |
|---|---|---|
| behavior | A stakeholder could observe the difference | Yes |
| data | The shape or meaning of a noun is undefined | Yes, against the entity model |
| mechanism | How it is built | No. It would be a finding if the specification *did* say it |
| free | Deliberately open; may vary between implementations | No, unless nobody decided it was free |

A behavior item is a `warning` when two reasonable implementers would build
visibly different things, `info` when the difference is cosmetic.

Words that always produce an item: appropriately, relevant, etc., handles,
notifies (of what?), shows the (which details of the?), validates the (against
which rule?).

## The ten recurring mistakes, by reading

| Mistake | What it looks like | Found in |
|---|---|---|
| No system | Only actor actions; the system never does anything | 2 |
| No primary actor | Written from inside: "Validate code. Issue ticket." | 1 |
| Screen walkthrough | Prompts and entries step by step | 1, lint `UI_DETAIL` |
| Goal too low | A technical step as a use case | 1 |
| Purpose and content differ | A small use case that quietly specifies the whole application | 1 |
| Mechanism leakage | Protocols, storage, code vocabulary | lint `MECHANISM_TERM`; 3 for what the list misses |
| Restated truth | Entity attributes, quality thresholds or mockup detail copied in | cross-file checks |
| The open flow | No ending, a validation without a flow, an "ends" without a guarantee | lint; 2 |
| The blank check | "Appropriately", "handles the error", "the relevant data" | lint `WEAK_WORD`; 3 |
| Backfilled specification | Code changed first, the file "updated later" | Not visible in a file; the coverage audit finds it as drift |

## What is not a finding

- Behavior the specification could have had but nobody asked for. The yardstick
  is the requirement, not your idea of a better product.
- Style. Wording that every reader understands the same way is fine.
- A general doubt ("edge cases may be missing"). Name the step and the
  condition, or do not report it.
- Anything the lint already reported for the same element.
