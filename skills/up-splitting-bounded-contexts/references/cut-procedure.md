# The cut procedure

How to carry out a split once the owner has decided on it.

## Contents

- Before the cut
- Layout
- Identifiers after the cut
- What goes where
- System-wide requirements
- Citations across contexts
- The move
- After the move
- The cross-context review
- Undoing a cut

## Before the cut

- The specification lint is clean on the whole set. Do not carry findings
  across a split; they become harder to see.
- No use case is mid-change. Slices in flight finish or are parked first.
- The context map is written and the owner has agreed to it.
- Each context has a named owning team or person.

## Layout

Two layouts work. The owner chooses.

**One repository, one folder per context.** Simplest to move to; history
stays in one place; one pull request can still (wrongly) touch two contexts,
so ownership rules matter.

```text
workshop/
├── docs/            requirements.md, entity_model.md, use_cases.puml, use_cases/, test_cases/
├── AGENTS.md        guideline file of this context
└── ...              this context's code and tests
billing/
├── docs/
├── AGENTS.md
└── ...
docs/
└── context-map.md   contexts, owners, contracts
```

**One repository per context.** Strongest boundary; each context has its own
history and pipeline by construction; the context map and the contracts need
a home that every team can read.

Context names are lowercase, one or two words joined by a hyphen, the same in
folder names and citations.

## Identifiers after the cut

- Every existing identifier stays exactly as it is.
- Within a context, identifiers are unique. Across contexts they are told
  apart by the context name.
- A new use case, requirement or journey in any context is numbered above the
  highest identifier that existed before the cut. An identifier that existed
  in the undivided set never comes to mean a second thing.
- Code markers and test names keep their identifiers. They live with the
  context's code, so they stay unambiguous.

## What goes where

| Element | Goes to |
|---|---|
| A use case file | Its context's `docs/use_cases/`, name unchanged |
| Its box in the diagram | Its context's diagram, with only that context's actors |
| An entity section and its diagram entry | The owning context's entity model |
| A relationship between entities of two contexts | Removed from both diagrams; replaced by a contract and a reference attribute on the consuming side |
| A functional requirement | The context whose use cases realize it |
| A journey test case within one context | That context |
| A journey test case across contexts | The context where the journey ends, named as its owner in the context map |
| A process model | The context that owns most of its activities; lanes of other contexts stay as they are |
| Decision records | With the context they concern; system-wide ones stay at the root |

An entity that two contexts both change is a sign the boundary is in the
wrong place, or that the entity is really two. Resolve that before moving.

## System-wide requirements

Some non-functional requirements and constraints bind every context (a legal
retention period, an accessibility standard). Give them one home: a small
catalog of a context named for it (commonly `platform`), with a named owner.
Use cases elsewhere cite them qualified, for example `platform/NFR-001`, on
their Requirements line. Do not copy the rows into every catalog; copies
drift.

## Citations across contexts

Inside a context nothing changes: `UC-012 BR-003`.

Across contexts the citation carries the context name:
`workshop/UC-012 BR-003`. The lint reports it as `EXTERNAL_REF` and does not
resolve it, because a context's lint reads only that context. List the
external references of a context with:

```bash
python3 <lint script> --docs billing/docs | grep EXTERNAL_REF
```

Prefer citing a contract over citing another context's rule. A consumer that
depends on a provider's internal rule is coupled to something the provider
believes it may change freely.

## The move

1. Create a branch.
2. Create the target folders.
3. Move each file with the version control system's move command, so the
   history of each file follows it.
4. Split the files that hold several elements (catalog, entity model,
   diagram): create the new file from the rows and sections assigned to the
   context. This is the one step where content is cut and pasted; check each
   target against the assignment.
5. Commit: only moves and the mechanical split, nothing reworded.
6. In a second commit: qualify crossing citations, fix relative links,
   replace cross-context relationships by contract references.
7. In a third: guideline file, ownership rule and pipeline per context.

Keeping the commits apart lets a reviewer confirm that the first one changed
no meaning.

Dry run first: list every planned move as `from -> to` and have it confirmed.
Nothing is deleted by hand; after the moves the old folders are empty.

## After the move

- Run the lint per context. Errors are almost always unqualified crossing
  citations or broken relative links.
- Run the metrics script per context: each should show its own clusters, and
  no entity that belongs elsewhere.
- Each team reads its own context once, end to end. It is the first time the
  set is small enough to do so.

## The cross-context review

Someone must notice when a rule in one context contradicts an assumption in
another. Name that person or group; "everyone" notices nothing.

Agenda, at a fixed rhythm and whenever a contract changes:

1. Contracts changed since the last review: is every consumer still served?
2. External references per context: do the cited elements still exist and
   still say what the consumer assumes?
3. Rules in different contexts that speak about the same business fact: do
   they agree?
4. New shared nouns: has a term started to appear in two contexts with
   different meanings?

A contract change is proposed by the provider and agreed by its consumers
before it is merged.

## Undoing a cut

If two contexts need a contract change for nearly every change, the boundary
is wrong. Merge them back: move the files into one context, drop the
qualifiers, and turn the contract back into ordinary references. Identifiers
stay, as always.
