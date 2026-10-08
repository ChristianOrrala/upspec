# Types and business rules

The entity model uses `Attribute | Meaning | Type | Rules`. Meaning says what
the value means to the business; Type comes from this closed vocabulary.

## Business types

| Type | Use for |
|---|---|
| Text | Words, addresses and other text |
| Number | Counts and measures |
| Money | An amount of money |
| Date | A calendar day |
| Date and time | A moment |
| Yes/No | A two-way fact |
| Identifier | How the business identifies an entity |
| Choice of A, B, C | A fixed set of named values |
| Reference to ENTITY | Another entity named in the model |

No storage length, precision, primary key, sequence or foreign key belongs in
this model. Recover the business meaning from an existing schema and record
the schema evidence in the recovery ledger. Storage choices belong to implementation.

A `Reference to ENTITY` requires a relationship to that entity in the Mermaid
diagram; the diagram owns the relationship. `ENTITY_TYPE` rejects unknown
types; `REFERENCE_NO_RELATIONSHIP` reports a missing relationship.

## Rules

State business constraints in the Rules cell: Required, Optional, Unique,
never reused, inclusive bounds (`Min: X`, `Max: Y`) or a named format such as
`Format: Email`. The type owns the choice list; do not repeat it in Rules.
A limit belonging to one behavior goes in that use case's business rule.

## Rules that span attributes

After the table, write a line such as:

```text
**Constraints:** check_out is after check_in.
```

## Lifecycle

```text
**Lifecycle:** A → B → C; B → D
```

States are exactly the values of the state attribute's `Choice of …` type.
Chains read left to right and are separated by semicolons. `->` is accepted
in place of the arrow. Moves not listed are forbidden. Name forbidden moves
that someone could attempt in the hand-off: they may become rules or flows.

## Descriptions

One sentence per entity, distinguishing it from its neighbors. For example,
CUSTOMER is a person who brings bikes to the workshop and decides on estimates.
The Meaning column defines each attribute in business words, not how it is filled.
