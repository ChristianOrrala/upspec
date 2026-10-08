# Schema changes

A guarded procedure. Follow the steps in order. Do not skip a confirmation and
do not improvise commands.

A schema change comes from one place only: a difference in
`docs/entity_model.md`. If the code seems to need a column the model does not
have, the model changes first (`up-3-modeling-domain-entities`), then this
procedure runs.

## Rules that always hold

1. **A change is a new migration.** A migration that has been applied
   anywhere outside your own machine is never edited, renamed or deleted.
   Migration tools record what they applied and detect a changed file.
2. **Names, types and relationships come from the entity model.** Do not
   invent a concept in the schema that the model does not have.
3. **Storage choices are the project's.** Map the model's business types to
   the project's existing storage types by looking at existing migrations, not
   by preference.
4. **Use the project's migration tool and naming.** Read existing migrations
   to find the tool, the naming pattern and the next version. For example,
   Flyway versioned migrations are named `V<version>__<description>.sql` and
   are applied once, in order; other tools have their own patterns.
5. **Nothing destructive runs without an explicit yes.**

## Classify the change first

| Change in the entity model | Class |
|---|---|
| New entity; new optional attribute; new attribute with a default | Additive |
| Broader business limit; new allowed value | Additive |
| New Required attribute without a default on an entity that has data | Needs data |
| Renamed entity or attribute | Destructive if done in one step |
| Removed entity or attribute | Destructive |
| Narrower business limit or type; removed allowed value; new `Unique` | Destructive: existing data may violate it |

## Additive change

1. Write one new migration with the next version.
2. Apply it to a disposable database (a local or test instance created for
   this purpose) using the project's own command.
3. Run the project's tests against it.
4. Commit the migration with the specification change and the code.

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
