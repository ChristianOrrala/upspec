# Types and validation rules

The closed vocabulary of the entity model. Tools parse these cells; anything
outside the vocabulary is reported.

## Contents

- Data types
- Validation rules
- Rules that span attributes
- Lifecycle
- Descriptions

## Data types

| Data Type | Length/Precision | Use for |
|---|---|---|
| Long | 19 | Identifiers the system numbers in sequence, and references to them |
| String | number of characters | Text; a generated unique identifier (36 for the common form), and references to it |
| Integer | 10 | Whole numbers |
| Decimal | total digits, decimals (for example `10,2`) | Money, percentages, measures |
| Boolean | 1 | Yes or no |
| Date | - | A calendar day |
| DateTime | - | A moment |

Never a storage or framework type (`VARCHAR`, `TEXT`, `bigint`, `numeric`,
`uuid`, `timestamp`, `enum`). Never an invented type (`Money`, `Email`). A
fixed set of values is a `String` with a `Values:` rule; an email address is a
`String` with `Format: Email`.

The Length/Precision cell holds the bare value: `255`, `10,2`, `-`.

The identifier's type is a fact about each entity, not a default. When the
model is written from an existing schema, read it per table: a sequence is
`Long | 19 | Primary Key, Sequence`; a generated unique value is
`String | 36 | Primary Key`. A reference has the type of the identifier it
points to.

## Validation rules

Compose a cell from these phrases, separated by commas, in this order:

| Phrase | Meaning |
|---|---|
| `Primary Key` | Identifies the entity |
| `Sequence` | The value is assigned by the system, ascending |
| `Not Null` | Always present |
| `Optional` | May be absent |
| `Unique` | No two entities share the value |
| `Foreign Key (ENTITY.id)` | Refers to another entity of the model |
| `Min: X` / `Max: Y` | Bounds, inclusive |
| `Values: A, B, C` | The only allowed values |
| `Format: Email` | A named format |

Rules of composition:

- Every cell starts with `Primary Key`, `Not Null` or `Optional`. No cell is
  empty.
- `Values:` comes last, because its own list contains commas.
- Bounds are inclusive. If the business bound is exclusive, state the nearest
  inclusive value (`Min: 0.01` for "greater than zero" on a `10,2` decimal).
- A `Foreign Key` names an entity that has its own section, and the diagram
  has a relationship line between the two.

Typical cells:

```text
Primary Key, Sequence
Not Null
Not Null, Unique, Format: Email
Not Null, Foreign Key (CUSTOMER.id)
Optional, Min: 0.01, Max: 99999.99
Not Null, Values: Open, Assigned, Done
```

A cell may hold one phrase pattern or several, separated by commas; the
scripts accept both. One pattern per cell is the most portable form.

## Rules that span attributes

One line after the table:

```text
**Constraints:** check_out is after check_in.
```

State the rule in business words. If it belongs to one behavior only, it is a
business rule of that use case and does not go here.

## Lifecycle

```text
**Lifecycle:** A → B → C; B → D
```

- States are exactly the values of the state attribute's `Values:` rule.
- A chain reads left to right; chains are separated by semicolons. `->` is
  accepted in place of the arrow.
- A state no chain enters is the initial state. A state no chain leaves is
  final.
- Moves not listed are forbidden. Each forbidden move that someone could
  attempt is worth a sentence in your hand-off: it will become a business rule
  or an alternative flow.

## Descriptions

One sentence per entity, written so that it separates this entity from the
ones it could be confused with:

| Weak | Better |
|---|---|
| "Stores customer data." | "A person who brings bikes to the workshop and decides on estimates." |
| "A booking." | "A guest's claim on a room type for a date range, before check-in." |

The Description column of an attribute says what the value means to the
business, not how it is filled.
