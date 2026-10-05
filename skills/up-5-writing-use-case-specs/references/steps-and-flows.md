# Steps and flows

Each rule below removes one way a reader, human or agent, can misread a step.

## Contents

- The sentence
- Three kinds of step
- Intent, not movements
- "Validates"
- How many steps
- Repetition, order, optional steps
- Alternative flows: anchor, ending, nesting
- The closed loop

## The sentence

| Rule | Wrong | Right | What goes wrong otherwise |
|---|---|---|---|
| Name who acts, first | "Deduct the amount." | "System deducts the amount from the balance." | An agent assigns a subject, not always the one you meant |
| Active voice | "The amount is deducted." | as above | Who acts decides whether the step becomes interface, service or a call to another system |
| One actor per step | "Customer enters the code and system verifies it." | Two steps | A flow cannot anchor to half a step |
| Outside view | "Get card. Validate PIN." | "Customer presents the card. System validates ..." | Written from inside the system, the actor disappears, and with it everything the interface needs |
| Moves the goal forward | "User presses Tab." | Delete it | Noise hides the steps that matter |
| One rule per step | "System validates the user and assigns the task." | Two steps | They fail for different reasons and need different flows and tests |

An optional leading article is fine ("The customer selects ..."). Use the actor
names from the Overview exactly; "User" when the actor is "Customer" is a
second name for the same thing.

## Three kinds of step

| Kind | Looks like | Serves |
|---|---|---|
| Interaction | "Customer requests ...", "System shows ..." | The actor |
| Validation | "System validates that ..." | A stakeholder's interest: the business, a regulator, another user |
| State change | "System records ...", "System sets the status to ..." | Whoever relies on the result later |

A good scenario has all three. Missing validations and state changes are the
usual cause of a scenario with fewer than three steps.

## Intent, not movements

Six steps of prompt and entry are one step:

```text
1. Customer enters name and delivery address.
2. System shows the customer's profile.
```

Collapse everything that flows in one direction into one step and give the data
a name ("delivery address", "payment details"). The entity model says what the
name contains.

## "Validates"

"System checks whether the password is correct" leaves the outcome open and
turns the scenario into branches. "System validates that the password is
correct" asserts success; the failure goes into a named flow.

One validation per rule, one flow per validation, one outcome the actor can
see per flow. That gives the implementing agent its error handling without a
single line about error handling.

## How many steps

Three to nine. More than nine nearly always means screen mechanics crept in or
the goal is a level too low: merge steps by asking why the actor does them. The
last step delivers the goal in a way the actor can observe ("System confirms
... and shows ..."), not a passive statement that something "is done".

## Repetition, order, optional steps

Say it in a sentence, never in code:

- "Customer repeats steps 3 and 4 for each item."
- "Steps 2 to 4 may occur in any order."
- "Customer may skip step 3."

## Alternative flows: anchor, ending, nesting

**Name** the flow after the condition: `### A2: Loan Limit Reached`.

**Trigger** states what the system detected, not what happened in the world,
and names the step: `**Trigger:** The member already has 5 open loans (step 5)`.
For a condition that can arise over a range or at any moment, write
`(steps 2-6)` or "at any time".

**Ending** is one of exactly two sentences as the last line:

```text
Use case continues at step N.
Use case ends.
```

A retry returns to the step where the actor acts again. A different route to
success continues at the step where the routes meet. Total failure ends.

**"Ends" has a price.** Whatever the flow leaves behind must be covered by the
failure postconditions. If a flow would leave something half done, either the
flow needs a step that undoes it or the postconditions are incomplete.

**Nesting.** A condition inside a flow may get a step of its own. At the second
level stop: either the flow is its own use case (rare, only when really
shared), or you are specifying below the user's goal.

## The closed loop

Check this before running the validator, which checks it again:

```text
every main step succeeds              → no "if", no branch
every "validates"                     → answered by one flow anchored to that step
every flow                            → trigger with (step N), one of two endings
every "Use case ends."                → backed by a failure postcondition
every (BR-XXX) cited                  → defined below
every rule defined                    → cited by a step or a flow
```

Nothing dangles. An agent cannot leave a path unhandled without contradicting a
line you wrote.
