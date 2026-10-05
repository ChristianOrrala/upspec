# Code as evidence

What each kind of code tells you about intent, and what it cannot.

## Contents

- Entry points by kind
- The project's own words
- Specifications of another method
- From code to specification text
- Actors
- Entities
- What evidence does not prove
- Things that are not use cases
- Order of work on a large system

## Entry points by kind

| Entry point | Suggests | Actor | Trigger |
|---|---|---|---|
| A screen, page or view | A use case, or part of one | The role allowed to reach it | That role's request |
| An interface endpoint called by another system | A use case or a step | The calling system | Its request |
| A scheduled job | A use case | Scheduler | A point in time |
| A message or event consumer | A use case or a step | The system that sends the message | The message |
| A command-line command | A use case for an operator | Operator | The command |
| An import or export path | A use case | The role or system that supplies or receives the file | The delivery, or a time |
| A screen flow handled entirely in the front end | A use case or an alternative flow of one | The role on that screen | That role's action |
| A flow configured in a hosted service (identity, payment, messaging): sign-in, password reset, sign-up confirmation | A use case or an alternative flow, with the service as a secondary actor | The role that starts it | That role's action |

Front-end and hosted flows have no server route of their own, so a reading of
the server alone misses them. Read the front end's routes and the
configuration of every hosted service the system uses; what the user sees on
those screens is recovered like any other behavior.

Several entry points usually serve one goal: a form to show, a submission to
accept and a confirmation to display are one use case. A wizard is one use
case. A list, a detail view and an edit of the same thing are usually one.

## The project's own words

Before naming actors, use cases and entities, look for the words the project
already uses: a glossary, a product document or a vision, the help texts and
labels on its screens. Specifications use those words. A word only the code
uses (a table name, an internal status) is not one of them.

Where two documents name the same thing differently, or a document and the
screens disagree, list the conflict as an open decision for the owner. Do not
choose, and do not coin a third word.

## Specifications of another method

Spec Kit's `specs/`, Kiro's `.kiro/specs/`, OpenSpec's `openspec/` and loose
specification documents are evidence of the same rank as a product document:
they say what someone meant the system to do, not what it does. Read them
beside the code. Each recovered use case cites the document it drew on in
the ledger, as it cites code. Where a document and the code disagree, list the conflict for the owner;
where a document promises behavior the code does not have at all, it is a
change log entry of kind `Claimed but not built`, citing the document's
line. The old documents stay where they are until the
baseline review is done and the owner says yes; then `scripts/relink.py`
moves them to `docs/recovery/sources/` (for example
`--move specs docs/recovery/sources/specs`), rewriting the ledger's citations
(`path:line`) and every link, and `check_recovery_ledger.py` stays clean.

## From code to specification text

| In the code | In the specification |
|---|---|
| A route or handler that creates something and answers success | "System records the reservation." |
| A check on entry that rejects when not signed in or lacking a role | A precondition, or the primary actor |
| A condition that rejects input the actor gave during the flow | A validating step, an alternative flow, and usually a rule |
| A validation annotation or schema constraint on input | A rule in business words: "An email address is required." |
| A numeric constant in a condition | A rule with that quantity and boundary examples taken from the comparison operator |
| An exception type and its handler | An alternative flow named after the condition, not the exception |
| A call to a mail, payment or other outside service | A step ("System sends the customer a confirmation") and a secondary actor |
| A transaction boundary, a rollback, checks before any write | A failure postcondition: "Nothing is recorded." |
| Writes on success | Success postconditions |
| An error response or message | A step of the alternative flow saying what the message tells the actor, in the specification's language |

Boundary examples come from the operator: `count >= 5` rejecting means "at
most 5; a fifth is refused" only if you read it right. State what the code
does and mark it suspect if the comparison looks off by one.

Screen wording is paraphrased. Quote the exact words only where a rule depends
on them (a keyword the actor must type, a notice whose wording is the rule),
in the language of the screen, without emoji or formatting. A specification
that quotes every message is long, and its reader learns the copy instead of
the behavior.

Not every constant is a business rule. A limit the business set (five open
loans, a 30-day refund period) is a rule. A limit of the implementation (a
timeout, a retry count, a page size, a token budget, a polling interval) is
not: put it in the ledger as a note on the rule or flow it affects. If a user
can notice it, it may later become an NFR row; that is the owner's call.

## Actors

- Role and permission definitions give the names. Use the business's word for
  the role if the code's differs and you know it; otherwise the code's, and
  say so.
- An area open without authentication has an unauthenticated actor (Visitor).
- If the code has only one role, there are still usually two actors: visitor
  and signed-in user.
- Schedulers and external systems are actors.

## Entities

Sources in order of authority:

1. **Schema migrations or the schema itself.** The database is what runs.
2. **Model classes.** Names, relationships and validation the schema does not
   show.
3. **Transfer and form classes.** Only when nothing else declares the shape.

Translate, do not copy:

- Table and class names become business nouns in upper snake case.
- Storage types become business types. The identifier's type is read for
  every entity from its own table: a number the system assigns in sequence and
  a generated unique value are different facts (one tells how many exist and
  in which order, the other does not). Never carry one entity's identifier
  type over to the next.
- A nullable column is `Optional`; a constraint becomes a validation phrase.
- A status column's values come from the code that writes it; its lifecycle
  from the transitions the code performs.
- A constraint the code relies on but the schema lacks is written into the
  model and noted as suspect: "uniqueness is assumed by the code and not
  enforced".

The description says what the entity means, which the schema does not know.
Read the code that uses the table before writing it. If a row can play two
roles, say so.

## What evidence does not prove

| You see | You may not conclude |
|---|---|
| Code that does something | That anyone wanted it |
| A validation | That it is reachable from every entry point |
| A constant | That it is a decision; it may be a leftover |
| A test | That it reflects current intent; it may pin an old bug |
| A comment or a document in the repository | That it is true, or current |
| No code for a case | That the case cannot happen |

Each of these is a reason for a `suspect` row, not for a correction.

Evidence is the line that decides: the condition that refuses, the write that
records, the constraint in the schema. A function's first line or a module's
entry point is not evidence; the second reader cannot check a claim against it.

## Things that are not use cases

- Health checks, metrics, static assets, framework callbacks.
- Internal helpers reachable only from other code.
- Administrative back doors used once. List them as unclassified and ask.
- A bucket. A use case named after an area of the system (*Operate the
  Platform*, *Manage the System*) whose entry points serve unrelated goals.
  Split it by goal; entry points that serve engineers running the system
  (migrations, seeding, one-off repairs) are usually not use cases at all.

Report every entry point you did not classify. Honest gaps are more useful
than invented use cases.

## Order of work on a large system

1. One pass over the tree to list every entry point file.
2. Cluster by feature; directory and package names usually show the clusters.
3. One cluster at a time: actors, use cases, ledger rows.
4. The data layer once, at the end; entities are shared across clusters.
5. Ask the owner how deep the specifications go; then write them, one
   cluster at a time.
