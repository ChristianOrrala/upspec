# Schema changes

A guarded procedure. Follow the steps in order. Do not skip a confirmation and
do not improvise commands.

## Contents

- Where a schema change comes from
- Rules that always hold
- Classify the change first
- Additive change
- Technical change
- Change that needs data, or is destructive
- Never
- Report

## Where a schema change comes from

A schema change that adds or changes a business concept starts in the entity
model: a difference in `docs/entity_model.md` is where it comes from. If the
code seems to need a column the model does not have, the model changes first
(`up-3-modeling-domain-entities`), then this procedure runs.

Only a change no flow can observe comes from an engineering decision instead:
an index or partitioning. It makes the same data faster to reach or easier to
keep, and no user could tell it happened. Triage classifies it as no behavior
change (triage outcome 7, `up-1-triaging-change-requests`), and the change
carries the line `No behavior change: UC-012`, naming the use case whose code
it touches, or `none` and the reason. It follows the technical path below.

A key, a uniqueness constraint or a version column is not technical, even
when an engineer proposes it. A user can observe each one: a record refused
because another already has the same value, a save refused because someone
else saved first. It goes through the model (an `Identifier`, a `Unique` rule,
or a rule on changes made at the same time) like any other business concept.
The key meant here is one that tells records apart for the business.

The model leaves out the keys of the storage itself: `up-3-modeling-domain-entities`
lists primary keys, sequences and foreign keys as mechanism. They follow from
the model; they are not a way around it, and none of them takes the technical
path. The storage's own record key and its sequence come with the entity they
belong to and change with it. A foreign-key constraint enforces a relationship
the model states (a relationship in the diagram and a `Reference to`
attribute): it is part of the change that adds that relationship.

Added later, for a relationship the model already states, a foreign-key
constraint is the code catching up with the model: triage outcome 1, the code
does not match the model. It takes the destructive path below, because
existing rows may violate it: the explicit yes, the count of violating rows,
and the parts the classification names. The entity model stays unchanged. The
commit message names the relationship it enforces, as the model writes it, and
carries the note `Fixes: UC-012`, naming the use case whose relationship it
enforces (the one whose flow records the reference); the spec-first guard
reads that note, as it reads the light path's. A foreign-key constraint for a
relationship the model does not state means the model changes first.

When you cannot tell whether a flow could observe a change, it goes through
the model.

## Rules that always hold

1. **A change is a new migration.** A migration that has been applied
   anywhere outside your own machine is never edited, renamed or deleted.
   Migration tools record what they applied and detect a changed file.
2. **Names, types and relationships come from the entity model.** Do not
   invent a concept in the schema that the model does not have. A technical
   change adds no column a flow could read and no business name: an index or
   a partition takes its name from the project's existing pattern, over
   columns the model already explains.
3. **Storage choices are the project's.** Map the model's business types to
   the project's existing storage types by looking at existing migrations, not
   by preference.
4. **Use the project's migration tool and naming.** Read existing migrations
   to find the tool, the naming pattern and the next version. For example,
   Flyway versioned migrations are named `V<version>__<description>.sql` and
   are applied once, in order; other tools have their own patterns.
5. **Nothing destructive runs without an explicit yes.**

## Classify the change first

| Change | Class |
|---|---|
| New entity; new optional attribute; new attribute with a default | Additive |
| Broader business limit; new allowed value | Additive |
| A version column: the model's rule that a change made on an outdated copy is refused, with a starting value for existing rows | Additive in data; observable, so it comes from the model |
| New Required attribute without a default on an entity that has data | Needs data |
| Renamed entity or attribute | Destructive if done in one step |
| Removed entity or attribute | Destructive |
| Narrower business limit or type; removed allowed value | Destructive: existing data may violate it |
| New `Unique`, or a new or changed key that tells records apart (`Identifier`) | Destructive: existing rows may already share the value |
| A foreign-key constraint added to existing data, for a relationship the model already states (triage outcome 1: the code catching up with the model) | Destructive: existing rows may violate it; the model stays unchanged |
| Index or partitioning, with no change in the entity model | Technical: triage outcome 7 |

Every row but the last comes from the entity model: a difference in it, or,
for the foreign-key row, a relationship it already states.

## Additive change

1. Write one new migration with the next version.
2. Apply it to a disposable database (a local or test instance created for
   this purpose) using the project's own command.
3. Run the project's tests against it.
4. Commit the migration with the entity model change, the specification
   changes it led to, and the code.

## Technical change

An index or partitioning, classified by triage as outcome 7.

1. Check the class once more: if any flow could observe the change (a refused
   record, a different order of results, a new limit), it is not technical.
   Stop and send it through the model.
2. Write one new migration with the next version. It adds no column a flow
   could read and no business name.
3. Apply it to a disposable database and run the project's tests against it.
4. Commit the migration, and any code it needs, with the line
   `No behavior change: UC-012` (or `none` and the reason). Nothing else: no
   entity model or specification change, no change record.

## Change that needs data, or is destructive

Split it. Each part is its own migration and can be released on its own.

| Part | What it does | Reversible |
|---|---|---|
| 1. Expand | Add the new structure next to the old. Nothing is removed | Yes |
| 2. Migrate | Copy or compute the data into the new structure | Yes, the old data is still there |
| 3. Switch | Code reads and writes the new structure | Yes |
| 4. Contract | Remove the old structure | **No** |

Procedure:

1. State the classification and the parts to the owner. Say which data would
   be lost by part 4 and that it cannot be undone.
2. Write parts 1 and 2. Apply them to a disposable database that holds a copy
   or a realistic sample of the data. Check row counts and a few values.
3. For a new constraint on existing data, first count the rows that would
   violate it. If any exist, stop and report the count. What happens to those
   rows is a business decision, not yours.
4. Do part 3 in code.
5. **Part 4 only after an explicit confirmation** that names what is removed,
   and only as a separate change. Before it: confirm a backup exists that the
   owner can restore from. Do not create the contract migration "for later" in
   the same change.
6. Commit the first parts with the entity model change they come from and
   the specification changes it led to (part 4 later, on its own, as step 5
   says). A foreign-key constraint for a relationship the model already
   states has no model change: its commit names the relationship and carries
   `Fixes: UC-012`, naming the use case whose relationship it enforces.

## Never

- Run a migration against a shared or production database yourself. You apply
  to disposable databases; the project's pipeline applies elsewhere.
- Drop, truncate or rewrite data in a test run to make a migration pass.
- Edit an applied migration to fix it. Write a new one.
- Rename by drop and recreate.
- Put a credential or a connection string in a migration, a script or a
  report.

## Report

```text
Entity model change: WORK_ORDER gains priority (Choice of Low, Normal, High; Required)
Class: needs data (Required attribute on an entity with existing data)
Migrations written: expand (nullable column), migrate (existing rows: Normal)
Applied to: disposable local database, 1,204 rows, 0 nulls after migrate
Not done: contract (set Not Null). Needs confirmation; separate change.
```

For a technical change:

```text
Engineering decision: index on WORK_ORDER drop-off date (no entity model change)
Class: technical (triage outcome 7)
Migrations written: one (create index)
Applied to: disposable local database; tests pass
Commit line: No behavior change: UC-001
```
