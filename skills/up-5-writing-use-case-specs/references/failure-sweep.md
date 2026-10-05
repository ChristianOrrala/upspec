# Finding alternative flows

Most of a system lives in its alternative flows, and so do most of the
requirements nobody stated. A forgotten condition used to come back as a
developer's question. Now it comes back as invented behavior. Work in three
passes and keep them apart: working out the handling drains the attention
needed to find the conditions.

## Pass 1: brainstorm every condition

Go through the main scenario step by step and ask each question of each step.
Write conditions only, no handling.

| Sweep | Ask | Typical conditions |
|---|---|---|
| Validations | How can each "validates" fail? | Limit reached, state not allowed, value out of range |
| Other ways to succeed | Is there a shortcut, a pre-filled value, a different valid choice? | Actor declines instead of approves; a saved address is reused |
| The actor errs | Wrong, incomplete or contradictory input? | Required information missing, a date in the past |
| The actor goes silent | What if they stop halfway? | No decision within the time allowed |
| A secondary actor | Refuses, answers wrongly, or does not answer? | Payment declined, message service unreachable |
| **Not allowed** | May this actor do this, to this thing, now? Someone else's record? | Not the owner; role lacks the right; attempted on another customer's data |
| **Changed meanwhile** | What if someone else changed it between step N and step M? | The last copy was taken; the price changed; the record was closed |
| **Twice** | What if the same request arrives again? | Double submission; a retry after a timeout that did succeed |
| **Time** | Does a deadline, a cut-off or "today" matter? In whose time zone? | Expired at midnight; requested on the last valid day |
| **Earlier attempt** | Did a previous run stop halfway? | A draft exists; a reservation is still held |
| **Nothing and the maximum** | What if there is nothing to show, or far too much? | No items match; the list exceeds what can be shown |
| The entity's lifecycle | Which state moves does the entity model forbid? | Approving a declined order; reopening a collected one |
| Internal failures treated as business | Can the system detect a failure of its own that the business has a rule for? | A dispenser jams; a document cannot be produced |

The rows in bold are the ones first drafts miss.

## Pass 2: rationalize

Keep a condition only if the system can **detect** it and the business wants it
**handled**.

- Not detectable: rewrite as what the system sees. "Customer forgot the code"
  becomes "no code entered within the time limit".
- Same net effect: merge. "Card scratched", "reader broken" and "not a card of
  this bank" are one flow: "Card unreadable".
- Sub-failures: roll up. The flow says "the document cannot be stored", not the
  five reasons why.
- Covered by a precondition: drop it. If the actor must be signed in before the
  use case starts, "not signed in" is not a flow here.
- Purely technical with no specific business response (the database is down, a
  network timeout): no flow. The general response is a project-wide rule in the
  guideline file, and the failure postconditions state what stays true. A
  technical failure becomes a flow only when the system can detect it **and**
  the business response is specific to this use case.

If nothing survives for a step, that is a result, not a gap.

## Pass 3: write the handling

Now each surviving condition becomes a flow: name, trigger with its step, the
steps (what the system tells the actor is content, so state it), one of the two
endings.

For each flow decide where it ends:

| The actor ... | Ending |
|---|---|
| gets another try at the same input | continues at the step where they act |
| reaches the goal by another route | continues where the routes meet |
| does not reach the goal | ends; check the failure postconditions cover it |

## What a condition usually turns into

| Condition | Usually becomes |
|---|---|
| A limit or eligibility test | A business rule, a validating step, a flow |
| A state the entity may not be in | A precondition if established elsewhere; otherwise a validating step and a flow |
| Not allowed for this role | A precondition (role) or a validating step (ownership) |
| Changed meanwhile, twice | A validating step at the moment of recording, and a flow; often the failure postcondition already says the right thing |
| A deadline | A business rule with boundary examples in the workshop's or the customer's time zone, stated |
| A secondary actor fails | A flow that says what the actor learns and what is not recorded |

## When to stop

Stop brainstorming when a full sweep adds nothing. Stop writing when every
surviving condition has a flow and every "ends" is covered. Do not specify
flows for features nobody asked for: a condition about bulk operations has no
place in a use case that handles one item.
