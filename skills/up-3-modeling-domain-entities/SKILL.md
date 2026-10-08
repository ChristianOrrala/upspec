---
name: up-3-modeling-domain-entities
description: >-
  Creates or updates docs/entity_model.md: a Mermaid erDiagram of entities and relationships,
  attribute tables with business meanings, types and rules, lifecycle states and avoided words.
  Checks specification nouns and lists use cases affected by a model change. Use when the user
  asks for an entity, domain or data model or glossary, changes an entity or attribute, asks to
  resolve conflicting vocabulary, or a specification names a missing concept. Not for database
  migrations or ORM code.
---

# Modeling domain entities

Produce `docs/entity_model.md`. It does two jobs, in this order of importance:

1. **Vocabulary.** Every business noun the specifications use is defined here
   once. There is no separate glossary.
2. **Data shape.** Attributes, types and validation rules, precise enough to
   derive a schema from and no more.

It is not a schema. Table names, storage types, indexes and keys chosen for
technical reasons do not appear. The model should read the same on any stack.

Shared paths and identifiers: [references/conventions.md](references/conventions.md).

## The document

Start from [templates/entity_model.md](templates/entity_model.md).

**Diagram.** One Mermaid `erDiagram`. Entity names and relationships only: no
attribute blocks. An entity without relationships is listed on a line of its
own. The diagram shows structure at a glance; the tables own the detail, so
nothing is written twice.

```text
CUSTOMER ||--o{ BIKE : "owns"
```

| Left | Right | Meaning |
|---|---|---|
| `\|\|` | `\|\|` | exactly one |
| `\|o` | `o\|` | zero or one |
| `}o` | `o{` | zero or more |
| `}\|` | `\|{` | one or more |

**One section per entity**, a level-three heading with the name in
`UPPER_SNAKE_CASE`, then:

1. One sentence that says what the entity *is* and tells it apart from its
   neighbors. Not what it contains.
2. Optional `**Not:**` line: the words that must not be used for this concept.
3. The attribute table, four columns in this order:
   `Attribute | Meaning | Type | Rules`.
4. For an entity with a state: a `**Lifecycle:**` line.
5. Optional `**Constraints:**` line for rules that span attributes.

Types use a closed business vocabulary; rules express business constraints:
[references/types-and-rules.md](references/types-and-rules.md).

## Vocabulary guard

Two words for one concept is how a specification starts to contradict itself:
one use case says "loan", another "borrowing", and an agent builds two things.

- Choose the word the business uses. Singular.
- List the rejected synonyms on the entity's `**Not:**` line. The check script
  reports every place a specification uses one of them.
- A noun that appears in a requirement or a use case and is not an entity, an
  attribute or a role is a finding: add it, map it to an existing entity, or ask.
- Roles (Customer as an actor) and entities (CUSTOMER as data) may share a
  name. Generic words (system, data, list, screen) are not entities.

## Lifecycle

If an entity has an attribute that holds its state, write the states and the
allowed moves between them:

```text
**Lifecycle:** Booked → Diagnosed → Approved → Completed → Collected; Diagnosed → Declined; Booked → Cancelled
```

Chains are separated by semicolons. Every state must be one of the attribute's
`Choice of …` type. This line earns its place: each move that is *not* listed is a
candidate business rule and a candidate alternative flow for the use cases that
touch the entity ("a Declined work order cannot be approved"). Say so in your
hand-off; do not write the rules here.

## What the model must not contain

| Tempting | Why not | Where it goes |
|---|---|---|
| `VARCHAR(255)`, `bigint`, `uuid` | Storage, not business | Types from the vocabulary; the migration chooses storage |
| Join tables, audit columns, primary keys, sequences and foreign keys | Mechanism | The implementation |
| Behavior ("is created when the customer books") | Belongs to a use case | The use case specification |
| A limit that belongs to one behavior ("at most 8 per day") | A business rule | The use case that enforces it |
| A second copy of an attribute list in prose | Two copies drift | Nowhere |

## Workflow

1. Read `docs/requirements.md` and the existing model, if any. Read the use
   case specifications that exist, for their nouns.
2. Collect nouns: roles, business objects, states, events. Merge synonyms;
   choose one word; note the rejected ones.
3. Write the diagram: names and relationships only.
4. Write one section per entity: description, `**Not:**` line where synonyms
   exist, attribute table.
5. For each entity with a state attribute, write its lifecycle.
6. Run the check and fix what it reports:

   ```bash
   python3 scripts/check_entity_model.py
   ```

   The script is in this skill's folder; use the base directory shown when the skill
   was loaded, and do not search the disk for it.
7. On an update, produce the impact list (below).
8. Hand over: what was added or changed, the forbidden lifecycle moves that
   look like business rules, and anything you had to assume.

## Changing the model

A change to an entity is a change to every specification that uses the noun.
After any update, list:

- **Use cases** whose text uses the entity or the changed attribute. Search
  `docs/use_cases/` for the noun in its spoken form ("work order" for
  `WORK_ORDER`).
- **Journey test cases** whose test data carries the attribute.
- **Schema follow-up:** whether stored data changes shape. Say that a migration
  is due; do not write it. That belongs to `up-7-implementing-use-cases`.

Change only what was asked. Renaming an entity is a vocabulary change: add the
old name to `**Not:**` and list every file that uses it.

## Validation

The check must exit 0. `ENTITY_TYPE` refuses an unknown business type;
`REFERENCE_NO_RELATIONSHIP` refuses a reference without a diagram relationship.
`OLD_FORMAT` (exit 5) calls for `up-migrating-spec-formats`. Then read the model once as a stakeholder would:

- Could a business person confirm every description without knowing the system?
- Does each noun in the requirements resolve to exactly one entity, attribute
  or role?
- Would this document still be true on a different stack?

A "no" is fixed in the model, not explained in the hand-off.

## Worked example

Requirements mention customers, their bikes, repairs, "jobs" and "work orders".

```markdown
### WORK_ORDER

One repair of one bike, from booking to collection.

**Not:** job, ticket

| Attribute | Meaning | Type | Rules |
|---|---|---|---|
| reference | Work order number | Identifier | Unique, never reused |
| bike | Bike under repair | Reference to BIKE | Required |
| status | Where the repair stands | Choice of Booked, Diagnosed, Approved, Declined, Completed, Collected, Cancelled | Required |
| estimate_amount | Estimated cost | Money | Optional, Min: 0.01, Max: 99999.99 |

**Lifecycle:** Booked → Diagnosed → Approved → Completed → Collected; Diagnosed → Declined; Booked → Cancelled
```

Hand-off notes for this entity: "job" was used twice in the requirements and is
now an avoided word; the lifecycle has no move from Declined to Approved and
none out of Cancelled, which the specifier of *Approve Estimate* should turn
into rules or flows.

## Next

`up-4-mapping-use-cases` uses the nouns; `up-5-writing-use-case-specs` refers to entities
by noun and never restates their attributes.
