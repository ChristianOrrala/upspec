---
name: up-4-mapping-use-cases
description: >-
  Finds the use cases a system needs and records them as the use case overview (docs/use_cases.md:
  a scope list and delivery order written by people, and an actor-goal table and Mermaid diagram
  generated from the use case files), creating a stub for each mapped use case. Tests user-goal
  level, aggregates or splits Manage-X goals, moves multi-role or waiting flows to BPMN, and
  checks functional requirement coverage. Use when the user asks which use cases exist or are
  missing, whether a goal is a use case, for a diagram or actor-goal list, to split or merge use
  cases, to decide scope, or to check requirement coverage. Not for writing one use case's steps,
  bounded contexts or draw.io.
---

# Mapping use cases

Decide which use cases the system has, and record the decision as
`docs/use_cases.md`. The diagram is the table of contents of the
specification set: it says what the system offers, to whom, and which
specifications still have to be written. It says nothing about how a use case
runs.

Choose goals at the right level, because every error here is multiplied
later: a goal that is too small
becomes a fragment with no home, a goal that is too large becomes a
specification nobody can review.

Shared paths and identifiers: [references/conventions.md](references/conventions.md).

## Actors, then goals

1. **Actors first.** A role played toward the system: a kind of person, an
   organization, another system, or time itself for anything that runs on a
   schedule. Roles come from the catalog's roles and needs and the vision.
2. **Goals per actor.** For each actor, what do they come to the system to
   get done? Write each as a short verb phrase in the actor's own words:
   *Book Repair*, never *Create Work Order Record*.

Keep this actor-goal list in your hand-off. It is the one view that shows the
whole system at once.

An external system the use case calls upon (a payment or message service) is a
secondary actor: drawn as an actor, connected from the use cases that need it.

## The level test

Every use case in the diagram is a user goal. One question decides:

> Would the primary actor recognize this as a complete thing they came to do,
> and leave satisfied when it is done?

Signs and repairs are in [references/goal-levels.md](references/goal-levels.md). In short:

| Finding | Repair |
|---|---|
| **Too low.** A step of something larger, often technical: *Validate ISBN*, *Load Customer*, *Send Email* | Ask "why is the actor doing this?" and fold it into the goal that answers. It becomes a step there |
| **Too high.** An area of work: *Manage Orders*, *Run the Workshop* | Ask "how?" and split into the goals it consists of |
| **A process in disguise.** The work passes to another role, waits for an outside event or a deadline, or runs in parallel for different actors | Each role's part is its own use case. The flow between them is a business process (`docs/processes/`), not a use case |

A precondition is not a use case relationship. "The customer is signed in" is
established by *Sign In*; do not draw an include for it.

## Aggregate, then split

Start a CRUD-like area as one use case: *Manage Parts*. It stays one while the
operations share an actor, preconditions and one flow shape with small
variations.

Split an operation out the moment it grows its own actor, preconditions or
business rules. If blocking a customer needs a reason, an approval and a
notice, *Block Customer* is its own use case and *Manage Customers* loses that
operation.

A small service ends up with roughly four to eight use cases. Many more
usually means goals that are too low.

## Scope: in and out

For every capability someone debated, decide In or Out and record it in the
Scope section of `docs/use_cases.md`, consistent with `docs/vision.md`.
Ten minutes here prevents weeks of drift,
and the Out list is what stops an agent from building things nobody asked for.

- A candidate that maps to an Out item is refused, with the item named.
- A candidate nobody listed is not silently In: ask, then record the answer.
- You may propose the wording of a scope entry. The decision is the owner's.

## The generated overview

Start from [templates/use_cases.md](templates/use_cases.md). People write
`system` in front matter, Scope and Delivery order. The generator writes an
actor-goal table and a Mermaid use case diagram (`usecase-beta`) between the
markers: the named system boundary holds one ellipse per use case labeled
`UC-XXX Name`, actors stand outside it, and plain lines join them. Never edit
between the markers.

- Create a stub per mapped use case: required use case front matter,
  `status: Draft`, and the body `Not written yet.` Link the requirements it
  realizes; `secondary_actors` is optional.
- Run `python3 scripts/use_case_map.py` to generate the overview from the files.
- Identifiers are `UC-` and three digits, assigned once. A removed use case's
  number is not given to another.
- The overview shows actors and goals. Shared behavior is cited in the
  specifications; it is not an extra diagram relationship.

When the project tracks its work in the A-files, end the mapping with a
proposal: for each new use case, the ability in `ABILITIES.md` whose `Specs`
line it joins, or a new ability when none fits. The owner accepts it; the
pairing contract in the conventions has the rule.

## Workflow

1. Read `docs/requirements.md`, the Scope section of `docs/vision.md`, and
   `docs/entity_model.md` for the nouns. Read the existing diagram if there is
   one; its identifiers stay.
2. List the actors, then the goals per actor. Include time and external
   systems.
3. Apply the level test to every goal. Fold, split, or move to a process.
4. Aggregate CRUD-like goals; split what has its own actor, preconditions or
   rules.
5. Settle scope questions with the owner; keep the vision and overview Scope
   consistent.
6. Create a stub per mapped use case, with the next free identifiers. Write
   Scope and Delivery order in the overview, then run `scripts/use_case_map.py`;
   never edit between the markers.
7. Run the check and fix what it reports:

   ```bash
   python3 scripts/check_use_case_map.py
   ```

   The script is in this skill's folder; use the base directory shown when the skill
   was loaded, and do not search the disk for it.
8. State the delivery order (below) and report every merge, split, move and
   refusal with its reason.

## Delivery order

The diagram has no order, and "which one first" should not be decided by
accident. End with a short ordered list:

1. The use case whose main success scenario delivers the system's central
   value. Its main scenario alone is the first slice.
2. Then the use cases that establish what others need as a precondition.
3. Then by business priority of the functional requirements they realize.

For each of the first three, one line of reason. Alternative flows are not
planned here; they follow once the main scenario has been seen working.

## Validation

- The check exits 0. Every mapped use case has a file, at least a Draft stub,
  and links the functional requirements it realizes. `STALE_OVERVIEW` means
  rerun the generator; `FRONT_MATTER` and `STUB` mean repair the file.
  `OLD_FORMAT` (exit 5) routes to `up-migrating-spec-formats`.
- Every functional requirement that is not Rejected or Deferred has a use case
  that will realize it. Name the pairs in the hand-off.
- Each name passes the level test and is in the actor's language.
- Nothing from the Out list is in the diagram.

## Worked example

Catalog: customers book repairs and decide on estimates; mechanics record
diagnoses; finished bikes should be collected; parts are kept in stock.

Candidates and decisions:

| Candidate | Decision | Reason |
|---|---|---|
| Book Repair | UC-001 | Customer's goal, one sitting |
| Check Slot Availability | Folded into UC-001 | A step; nobody comes only to check a slot |
| Handle Repair | Split; process | Passes from customer to mechanic and waits for a decision: a process with UC-001, UC-004, UC-002 as activities |
| Approve Estimate | UC-002 | Customer's goal |
| Send Pickup Reminders | UC-003, actor Scheduler | Runs on a schedule; secondary actor Message Service |
| Record Diagnosis | UC-004 | Mechanic's goal |
| Add Part, Edit Part, Remove Part | UC-005 Manage Parts | One actor, one flow shape |
| Take Payment | Refused | Out of scope per the vision |

Delivery order: UC-001 first (nothing else can happen without a booking), then
UC-004 (establishes the precondition of UC-002), then UC-002.

## Next

`up-5-writing-use-case-specs` specifies one use case at a time, in the delivery
order. A summary that became a process is the input of
`up-writing-journey-test-cases`.
