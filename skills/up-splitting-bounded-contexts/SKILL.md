---
name: up-splitting-bounded-contexts
description: >-
  Splits a specification set that has outgrown review into bounded contexts, each owning its own
  requirements catalog, entity model, use cases, guideline file and pipeline: measures the
  specification core, clusters use cases by shared entities and actors, proposes contexts named after
  business capabilities, assigns every requirement, entity and use case to exactly one context, turns
  shared data into explicit contracts, moves the files keeping identifiers and history, and sets
  ownership and the cross-context rule review. Use when the user says the specs are too big to review,
  several teams or agents collide in docs, asks how to scale spec-driven development to multiple
  teams, wants to split a monolith's specifications, or asks which use cases, entities or requirements
  belong to which context, such as Billing or Order Management. Not for splitting code into services
  without specifications.
---

# Splitting bounded contexts

One specification set works while one group can review all of it. Past that
point reviews turn shallow, changes collide, and rules in one area quietly
contradict assumptions in another. The remedy is to cut the set into bounded
contexts: each a business capability with its own requirements catalog,
entity model, use cases, guideline file and pipeline, owned by one team.

This skill measures, proposes a cut, and carries it out. **Whether to split,
and where, is the owner's decision.** A split is expensive to reverse; a
wrong one is worse than none.

It splits specifications. Cutting code into deployable services is a separate
decision that may follow the same lines later, or never.

Shared paths, identifiers and Status values: [references/conventions.md](references/conventions.md).

## Signals

```bash
python3 scripts/spec_core_metrics.py
```

The script is in this skill's folder; use the base directory shown when the skill
was loaded, and do not search the disk for it. It reports counts, which
use cases name which entities, the clusters that result, and the entities
that hold clusters together.

| Signal | Read from | What it says |
|---|---|---|
| Size | Counts of use cases, rules, entities | Whether one reviewer can still hold the set |
| Separate clusters | Clusters sharing no entity | A cut that costs nothing: the areas are already independent |
| Bridges | An entity whose removal separates a cluster | Where a contract could replace shared data |
| Collisions | Ask: how often do changes under `docs/` conflict, and between whom? | Whether people are in each other's way |
| Contradictions | Ask: has a review found rules in two areas that disagree? | Whether one model is serving two meanings |
| A noun with two meanings | The entity model's avoided words; descriptions that say "or" | The strongest signal of a boundary |

Numbers alone do not justify a split. Forty use cases one team reviews
comfortably are fine. Twelve use cases that two teams fight over are not.
Report the measurements and the two questions; do not assert a threshold.

Reasons **not** to split: the set is small and one team owns it; the pain is
unclear specifications, not their number (review them instead); every cluster
is held together by many shared entities (the cut would produce more
contracts than it removes dependencies).

## Finding the cut

1. Start from the clusters and bridges. A separate cluster is a candidate
   context. A bridge splits a cluster into candidates joined by one contract.
   Prefer a bridge that few use cases name: an entity most use cases of a
   group name is that group's core, not its boundary.
2. **Name each context after a business capability**: what the business
   would call that part of its work (*Booking*, *Billing*, *Workshop*). Not
   after a team, a technical layer or a system. If no business name fits, the
   group is not a context.
3. Check actors: a context usually serves a few actors with related goals. A
   candidate serving every actor is a layer, not a capability.
4. Check words: where one noun means two things, the boundary runs between
   the meanings, and each context gets its own entity with its own
   description.
5. Prefer few contexts. Two that hold is better than five that need a
   contract for every change.

## Assigning everything once

Every requirement, entity and use case belongs to exactly one context.
Write the proposal as lines of `<context> <element>` and check it:

```bash
python3 scripts/spec_core_metrics.py --assign assignment.txt
```

It lists elements assigned twice or not at all, entities used across
contexts, citations and journeys that would cross, and requirements linked
from more than one context.

- **Use cases:** by the capability their goal serves.
- **Entities:** to the context that creates and changes them. Others only
  refer to them, through a contract.
- **Requirements:** with the use cases that realize them. A requirement
  realized from two contexts stays with one; the other writes its own
  requirement for its part.
- **Journey test cases** that chain use cases of two contexts get a named
  owner: usually the context where the journey ends.

## Contracts

Whatever crosses a boundary becomes an explicit contract, owned by the
context that provides it.

- A contract names what is exchanged in business terms: the fact that is
  announced or the question that is answered, the identifying key, and the
  few attributes the other side may rely on.
- The consuming context refers to the contract. It does not read or copy the
  provider's entity model.
- A citation across contexts carries the context name:
  `billing/UC-003 BR-002`. The lint reports these as external and does not
  resolve them; the cross-context review does.
- How a contract is carried (an event, an interface, a shared key) is a
  technical choice that belongs in a decision record, not in the context map.

## Ownership

Each context has one owning team, one guideline file with the rules block,
and one pipeline that runs the lint and the guard on that context's `docs/`.
A team changes its own context freely and a neighbor's only through that
neighbor.

A recurring **cross-context review** looks only at contracts and at external
citations: has a provider changed something a consumer relies on, and do two
contexts state rules that contradict each other? Someone is named for it.

Layouts, the move itself and the review in detail:
[references/cut-procedure.md](references/cut-procedure.md).

## Workflow

1. Run `scripts/spec_core_metrics.py` and report the measurements, clusters
   and bridges.
2. Propose candidate contexts named after business capabilities, with the
   reason for each boundary and what each would own: its own requirements
   catalog, entity model and use cases. Say also what speaks against a split.
3. Ask about collisions and contradictions, and discuss signals and proposal
   with the owner. The decision to split is theirs; without it, stop here.
4. Assign every requirement, entity and use case to exactly one context;
   check the assignment with `--assign`; list what is shared.
5. Define a contract for each shared item and name its providing context.
   Record all of it in [templates/context-map.md](templates/context-map.md).
6. Show the move plan: every file, from where to where. After a yes, move
   the files on a branch with the version control system's move command so
   history follows. Keep every identifier, and say in the report that none was
   renumbered. Change nothing else in the same
   commit.
7. Give each context its guideline file, owner and pipeline.
8. Qualify the citations that now cross. Run the specification lint per
   context. Set up the cross-context review.

Moving files is the low-freedom part: plan, confirmation, a branch, one
commit of pure moves. Never delete the old tree by hand; the moves empty it.
If the version control system cannot be run where you work, move nothing by
other means: hand the owner the plan as the exact move commands to run.

## Validation

- Every element is in exactly one context; the assignment check reports
  nothing assigned twice and nothing unassigned.
- No identifier changed. No file was renumbered or renamed beyond its folder.
- The lint runs clean per context; every crossing citation is qualified.
- Each contract has one providing context and at least one consumer.
- The history of a moved file still shows its earlier revisions.

## Worked example

A workshop system with thirty use cases. The script reports one cluster of
thirty, and one bridge:

```text
Bridges (an entity whose removal separates a cluster)
  WORK_ORDER, named by 19 use cases, separates: UC-001 ... UC-017 | UC-018 ... UC-030
```

Use cases 1 to 17 concern booking and repairing; 18 to 30 concern invoices
and payments. The owner confirms that the two halves are changed by different
people who conflict weekly.

- Contexts: **Workshop** and **Billing**.
- `WORK_ORDER` is created and changed in Workshop: Workshop owns it.
- Contract, provided by Workshop: *Work order completed*, carrying the work
  order number, the customer and the agreed amount. Billing's `INVOICE`
  refers to the work order number and holds no other work order data.
- `UC-018 Issue Invoice` cited `UC-012 BR-003`. It becomes
  `workshop/UC-012 BR-003`.
- All thirty identifiers stay. New use cases in either context are numbered
  from `UC-031` upward, so no identifier ever meant two things.
