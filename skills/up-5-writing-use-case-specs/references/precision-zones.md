# Precision zones

Detail has two axes. Observable detail is cheap to write and worth a great
deal: every concrete statement takes a decision away from the implementing
agent. Mechanism detail is harmful: a human ignores bad architecture advice in
a specification, an agent follows it.

One test settles every case: could a stakeholder confirm it, and could a test
assert it, without looking inside the system? Then state it. Otherwise leave
it out.

## Contents

- Zone 1: observable behavior
- Zone 2: referenced, never restated
- Zone 3: mechanism
- What "observable" means without a screen
- Outcome versus mechanism, by interface
- A mechanism word that is a business noun
- Where the rest goes
- The three questions for every step

## Zone 1: observable behavior, concrete

For each step ask what the implementer would have to make up, and decide it
yourself:

- **What is shown, and in what order.** "System shows the open orders with
  number, customer name and total, newest first."
- **Exact quantities.** "Due 28 days from today", "at most 5", never "soon" or
  "a few". Say whether a limit includes its boundary; put examples in the rule.
- **What a message tells the actor.** The content, not the widget: "System
  informs the member that borrowing is blocked while loans are overdue and
  lists the overdue items." The second half is a requirement; without it,
  whether the member learns which items is someone's guess.
- **What is entered together.** One step per direction of data, with a name.
- **Order and optionality.** "In any order", "may skip step 3".

## Zone 2: referenced, never restated

| Belongs to | Refer to it by |
|---|---|
| Entity model | The business noun ("the delivery address"). Never list its fields |
| Requirements catalog | The identifier on the Requirements line. Never repeat "within 2 seconds" in a step |
| Another use case's rule | `UC-004 BR-002` |
| A mockup or an interface description | A link |

Two copies drift, and an agent settles the contradiction silently by picking
one.

## Zone 3: mechanism, left out

Protocols, storage, tokens and hashing, query language, HTTP verbs, status
codes, class and exception names, patterns, queues, caches, schedulers, file
formats chosen by developers, component and widget names.

"System securely stores the password" states the requirement. How it is done
today may change tomorrow, and the specification should survive that.

Screen vocabulary is mechanism too: no "dialog", "dropdown", "toast", "button".
Say what the actor decides, enters and learns. A label the business insists on
may be named as content ("the option *Decline*"). If you feel the urge to
describe a screen, a mockup is missing; link one.

## What "observable" means without a screen

| The use case is triggered by | Observable is |
|---|---|
| A person at a screen | What they see, decide, enter and learn |
| Another system's request | The business meaning of what it sends and what it gets back, and the state left behind |
| A point in time | What the run selects, what each recipient receives, what is recorded about the run |
| A message or event | Which event, what changes as a result, which event or notice follows |
| An operator | The signal they rely on: a record, a notice, a report |

The trigger line already allows a time or another system's message. The
primary actor is then the scheduler or that system, never "System".

## Outcome versus mechanism, by interface

| Write | Not |
|---|---|
| "Customer saves the reservation." | "Customer clicks the Save button." |
| "System validates the email address." | "System matches the email against a pattern." |
| "System informs the customer that ..." | "System throws a validation error." |
| "System signs the customer in." | "System issues a session token." |
| "Partner System requests the stock of a product." | "Partner System calls the stock endpoint with GET." |
| "System answers with the quantity available for sale." | "System returns 200 with a JSON body." |
| "System refuses the request and states that the product is unknown." | "System returns 404." |
| "Every day at 02:00 ..." (as the trigger) | "A cron job runs nightly." |
| "System delivers the invoices of the previous day to the Accounting System." | "System writes a CSV file to the SFTP folder." |
| "Payment Provider reports that the payment was captured." | "A webhook posts the payment event." |
| "System records the run with the number of invoices delivered." | "System writes a log line." |

## A mechanism word that is a business noun

Some domains own these words: a loyalty program issues tokens, a notary
service records hashes, a mail provider's product is a mail server. If the
entity model defines the word as an entity, it is vocabulary. Use it in that
meaning only. The validator then reports it as information instead of a
warning. Do not add an entity just to silence the validator.

## Where the rest goes

| You wanted to write | It belongs in |
|---|---|
| A response time or other quality threshold | An NFR row, linked |
| A field list or a format of a business noun | The entity model |
| A technical rule for the whole project | The guideline file |
| A one-off technical choice | A decision record |
| How a screen looks | A mockup, linked |
| How the code works inside | Nowhere |

Under-specification and over-specification are the same mistake: information
in the wrong artifact.

## The three questions for every step

1. Could a stakeholder confirm this step happened? If not, delete it or
   rewrite it as an outcome.
2. What would an implementer have to invent here? Specify it, refer to it, or
   declare it free.
3. Would the sentence still be true on a different stack next year? If not, it
   does not belong.
