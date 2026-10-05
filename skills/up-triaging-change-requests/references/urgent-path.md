# The urgent path

For a failure in production when time is short. It keeps the order
(specification, test, code) and removes everything else.

## Why there is no bypass

Under pressure the tempting sequence is: patch the code now, update the
specification later. Later does not come. After the first such patch the
specification is wrong in one place and nobody knows which. After a few, it is
decoration. Regeneration, traceability and a truth stakeholders can read all
rest on the fix going through the specification, especially when it is urgent.

So this skill never offers a code-only fix for a behavior change. If asked for
one, say why not in one sentence and offer this path instead.

## First: is a specification edit needed at all?

Read the element. Thirty seconds.

| The specification | Then |
|---|---|
| Is clear and right; the code violates it | No edit. This is the fastest case. Go to step 2 |
| Is silent or ambiguous about the situation | Step 1, smallest edit |
| Says what the system does, and that is what must change | Step 1, smallest edit. The owner or an on-call decision-maker confirms the change in one line |

## The path

1. **Smallest specification edit.** One rule's sentence, one boundary example,
   or one flow of two or three lines. Nothing else in the file. Status back to
   `Reviewed`.
2. **Failing test** named after the flow or rule, reproducing the failure with
   literal data.
3. **The fix**, touching only what the element requires, with the rule marker.
4. **One change set** containing the specification edit, the test and the fix.
   Subject names the use case.
5. **One reviewer reads the specification edit first**, then the test, then
   the code. For someone working alone: a fresh-context review of the edited
   element.
6. **Approval of the specification edit** by whoever may approve under the
   project's rules for urgent changes. Record who, in the change.
7. Release by the project's normal means.

## Afterwards, the same day

- Run the full review of the edited use case and the impact list. An urgent
  edit is small on purpose and may have missed a neighbor.
- Run the coverage audit before Status returns to `Tested`.
- If the edit was a stopgap, open the proper change now, while the context
  exists.

## What the urgent path does not allow

- A code change with no specification edit when behavior changes.
- Editing the specification afterwards to match what the code now does. That
  is writing history, not specifying.
- Skipping the failing test. Without it nothing shows the fault is gone, and
  nothing stops it from coming back.
- Widening the change "while we are in there".
- Destructive data repair as part of the fix. Repairing data that the fault
  already damaged is a separate, confirmed operation with its own rehearsal.

## A mitigation is not a fix

Switching a feature off, rolling back a release, or blocking a route changes
what users can do but is an operational action, not a behavior change of the
specification. Take it if the project's operations allow it. Then fix through
the path above. Note the mitigation in the change record so nobody mistakes
the mitigated state for the specified one.
