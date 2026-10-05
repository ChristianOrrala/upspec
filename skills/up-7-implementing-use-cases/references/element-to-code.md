# From use case element to code

Each part of a specification has a counterpart in code. The table says what
the counterpart is and how to tell it is really there. It holds for any stack;
the layer names are whatever the project calls them.

## The mapping

| Element | In code | It is there when |
|---|---|---|
| Primary actor | Who may reach this behavior: the access rule in front of it | Another role is refused before any step runs |
| Trigger | The entry point: a request handler, a scheduled start, a message consumer | The behavior starts on that event and on nothing else |
| Precondition | A guard in front of the behavior. Not a validation with a message | The behavior cannot be entered when the state does not hold |
| Interaction step (actor) | What the interface accepts | The named data can be given, together, as the step says |
| Interaction step (system shows) | What the interface returns or displays, in the stated content and order | Every named item is present, in order |
| Validating step | A check whose failure leads to exactly the flow anchored to it | Breaking the condition produces that flow's outcome |
| State-change step | A write | The state named in the step exists afterwards |
| Alternative flow | A branch: detect the trigger, run its steps, then return to the step named or end | The flow's last line is honored: "continues at step N" really returns there |
| Success postcondition | What is committed | All of it, together |
| Failure postcondition | What is left untouched or rolled back | After any failing path, the state equals the state before |
| Business rule | Enforcing code with its marker | Removing the code changes an outcome |
| Linked NFR | A limit the code respects | Stated where it can be measured; otherwise say that it was not measured |
| Linked constraint | A boundary the code stays inside | Nothing in the change crosses it |
| Secondary actor | An integration with something outside | The system calls it; it is not rebuilt inside |

## Things that are easy to get wrong

**A flow that silently falls through.** The trigger is detected, a message is
produced, and execution carries on down the main scenario. Check every flow's
exit.

**Failure postconditions treated as optional.** "No work order is recorded"
means the write happens after all validations, or everything is undone. If
several writes belong to one success, they succeed or fail together.

**A rule enforced only at the edge.** A limit checked where input arrives but
not where the state is written can be bypassed by another entry point. Enforce
it where the state changes; an additional early check for the actor's
convenience is fine and carries the marker too.

**The same request twice, or two at once.** If the specification's rules and
failure postconditions imply at most one result (one refund per order, one
open work order per bike), the check and the write must not be separable by a
second request.

**"Shows" without content.** If the step names columns, fields or message
content, those are requirements. If it names none, that is an invention-list
item, not a licence.

**Preconditions re-validated inside.** A precondition is established
elsewhere. Guard the entry; do not add a user-facing error for it inside the
flow unless a step says so.

## Without a screen

| Use case triggered by | Entry point | "System shows / informs" becomes | State after |
|---|---|---|---|
| Another system's request | The interface that system calls | The content of the answer, in business terms the specification states | As postconditions say |
| A point in time | A scheduled start | What each recipient receives; what is recorded about the run | As postconditions say; a run that stops halfway leaves what the failure postconditions allow |
| A message or event | A consumer | The event or notice that follows | As postconditions say; receiving the same message again changes nothing more |

## What not to build

- Anything no step, flow, rule or postcondition asks for: extra fields, extra
  endpoints, extra options, "useful" notifications.
- A general framework for future use cases.
- Handling for conditions the specification ruled out by a precondition.
- A secondary actor's own behavior.

If the code seems to need something the specification does not say (an error
with no flow, an input with no rule), that is a gap. Put it on the invention
list as `behavior` and ask.
