---
name: up-triaging-change-requests
description: >-
  Turns an incoming bug report, feature or change request, or production hotfix into a
  specification-first change: classifies it with the sign-off test (code wrong, specification wrong,
  test wrong, ambiguous specification, enhancement, new use case, or no behavior change), lists the
  affected requirements, use cases, rules, entities, journey test cases and tests, prepares the
  specification change first, resets the use case Status, and hands over to implementation and tests.
  Use when the user reports a bug or relays that users report something fails and asks to fix it, in a
  project that has use case specifications; forwards a stakeholder change such as a new limit, period
  or policy, asks whether something is a bug or a feature, wants an urgent fix or a production hotfix,
  says to patch the code now and fix the specification later, or asks what a change affects; it comes
  first, before any code is read. Not for diagnosing the technical root cause of a failure, not for
  projects without use case specifications.
---

# Triaging change requests

Work rarely arrives as a new use case. It arrives as a feature request, a
change of mind, a bug report, or an alarm in production. In a spec-driven
project all of them are the same kind of thing: a change to a use case. This
skill decides which kind, finds what it touches, and makes sure the
specification moves first.

It does not diagnose technical faults and it does not write the fix. It makes
sure that whatever is fixed or built afterwards has a specification behind it.

Shared paths, identifiers and Status values: [references/conventions.md](references/conventions.md).

## The specification is the arbiter

Read the use case before the code, whatever the report says. A bug report
describes a disagreement between what someone expected and what the system
did. Only the specification can say who is right. Reading code first answers a
different question: what the system does, which the reporter already told you.

## Classify

First restate the report as an element: which use case, which step, flow or
rule. If you cannot, the report is about behavior no specification describes.
Then find out whether the system already does it (next section) before you
choose between outcome 5 and 6.

Then apply the sign-off test:

> Would a stakeholder have signed off the specification as it stands, knowing
> what they want now?

- Yes: the specification said what everyone meant, and now they want
  something else. That is a change, not a bug.
- No: the specification never meant to say that, or the system does not do
  what it says. That is a defect.

| # | Outcome | It is when | Edit | Status of the use case | Then |
|---|---|---|---|---|---|
| 1 | Code wrong | The specification is clear and right; the system does something else | Nothing in the specification | Unchanged | The light path (below): a failing test named after the element, the fix, the note `Fixes: UC-012 BR-005`. A foreign-key constraint for a relationship the entity model states is the one exception: the destructive path of the schema procedure, with the owner's yes (The foreign-key exception, below) |
| 2 | Specification wrong | It says something nobody meant | The specification | Back to `Reviewed` | Review, approval, then synchronize |
| 3 | Test wrong | Code and specification agree; a test expects something else | The test | Unchanged | `up-8-deriving-use-case-tests` |
| 4 | Specification ambiguous | Two readers defend two readings; the code picked one | The specification, after the owner chooses | Back to `Reviewed` | As 2 |
| 5 | Enhancement | The specification is right for what was wanted then | The specification; perhaps a requirement | Back to `Reviewed` | As 2 |
| 6 | New use case | A goal no use case covers | Requirement, diagram, new specification | New file starts `Draft` | `up-2-cataloging-requirements`, `up-4-mapping-use-cases`, `up-5-writing-use-case-specs` |
| 7 | No behavior change | Refactoring, a dependency update, performance inside an existing threshold, infrastructure | Nothing | Unchanged | Proceed; the change carries the line `No behavior change: UC-012`, naming the use case it stays in |

Details and examples for each: [references/outcomes.md](references/outcomes.md).

## The light path

Triage writes a change record for the outcomes that change a specification:
2, 4, 5 and 6. The record is the agreement that the review, the
implementation and its finish check read. The other three outcomes change no
specification and get no change record.

- **Outcome 1, code wrong.** The specification already says what the code
  must do, so the fix costs a test and a line:
  1. A failing test named after the use case and the element the code breaks:
     a rule, a flow, a step, a precondition or a postcondition (for example
     `test_uc002_br005_sixth_loan_is_refused`, or the element's name inside a
     suite named after the use case). Run it and see it fail for the reason in
     the report.
  2. The fix, touching only what the element requires, with the rule's marker
     where it enforces a rule (`up-7-implementing-use-cases`, its light path).
  3. When the developer wants proof that the test guards the element, the
     guard check of that element (`up-8-deriving-use-case-tests`). Its verdict
     is information; nothing waits for it.
  4. The note `Fixes: UC-002 BR-005` in the commit message, naming the use
     case and the element. The spec-first guard and the agent hooks read it
     and do not report the change as code without a specification. Before
     the commit, the end-of-turn question comes once for the fix; the fitting
     answer is "at the end of the session" (the commit with its note closes
     it) or "now", not "later". A `Fixes:` line that names no use case, such
     as an issue reference, is not the note.

  No change record, finish check, test derivation or audit. Status stays where
  it is.
- **Outcome 7, no behavior change.** The line `No behavior change: UC-012`,
  nothing else.
- **Outcome 3, test wrong.** As before: `up-8-deriving-use-case-tests` fixes the
  test. Test files never count as behavior code.

If the failing test cannot be written because the specification does not
decide the case, it is not outcome 1: classify again (usually 4).

## The foreign-key exception

One outcome 1 names no element and does not take the light path: a
foreign-key constraint added later, for a relationship the entity model
already states (a relationship in its diagram and a `Reference to`
attribute). The code does not match the model, so it is code wrong, but
existing rows may violate the constraint: it takes the destructive path of the
schema procedure (`up-7-implementing-use-cases`, its schema changes reference),
with the owner's yes and a count of the violating rows. The model stays
unchanged. The commit names the relationship as the model writes it and
carries the note `Fixes: UC-012`, naming the use case whose relationship it
enforces (the one whose flow records the reference); the spec-first guard
reads it as it reads the light path's note.

## When the system already does it

A report can concern behavior the code has and no specification describes: a
box on a recovered map with nothing behind it, or a screen nobody mapped. That
is not outcome 6. A new specification written straight from the request would
mix two things the owner must keep apart: what the system does today and what
is being changed.

1. Write today's behavior first, as it is, at baseline depth and Status
   `Draft` (the procedure of `up-recovering-specs-from-code`; its ledger gets the
   rows). Add the use case to the map if it is missing.
2. Pin today's behavior with tests before anything changes
   (`up-8-deriving-use-case-tests`, against the code as it is).
3. Classify the request against that specification: usually outcome 5, or a
   defect.
4. In the change record, list every difference between today and after the
   change, one row each, with how today's behavior is known: read from the
   code, pinned by a named test, or observed. A row the request did not ask
   for is an invention: it needs the owner's yes, or it goes. Behavior only
   read from the code (above all an outside service's answers) is a guess until
   a test pins it. Observed means seen on the running system with its real
   services, by a person or by a test that calls the real service. A test that
   replaces the service with a stand-in pins only what the stand-in was told:
   a row that depends on the service's answer stays open until it is observed.

The differences table is the contract of the change. The review checks the
specification against it, and the implementation changes nothing that is not
in it.

Outcome 4 is the most valuable one to find: fixing the ambiguity improves every
later implementation. Outcomes 2, 4 and 5 are decided by the owner or a
stakeholder, not by you. State your classification and its reason, and ask.

## Find what it touches

```bash
python3 scripts/impact.py UC-002 "UC-002 BR-001" --code .
python3 scripts/impact.py "work order" --code .
```

The script is in this skill's folder; use the base directory shown when the skill
was loaded, and do not search the disk for it. Give it identifiers or
business nouns; it lists what refers to them:

- **Upward:** the requirements the use case links. Does the change alter what
  a requirement promises? Does it cross the scope written in the vision?
- **Sideways:** use cases that cite the rule or use the entity. A changed rule
  that another use case cites changes that use case too.
- **Downward:** journey test cases that include the use case, tests and code
  that carry its id, and whether the entity model changes (then a schema
  change follows).

Report the list. A change that touches three use cases is three
specification changes, each reviewed.

After adding a use case or changing its id, name, actors or goal, run
`python3 scripts/use_case_map.py --docs DIR`. Never edit between the overview
markers. Status changes need no regeneration.

## Specification first, always

For outcomes 2, 4, 5 and 6 the specification changes before any code:

1. Hand the specification change to `up-5-writing-use-case-specs` with what was
   decided.
2. Status goes back to `Reviewed`. It earns `Approved`, `Implemented` and
   `Tested` again. A `Done` use case that changes is not done.
3. Review, then a human approves.
4. `up-7-implementing-use-cases` synchronizes: only the changed behavior changes.
5. Tests follow the change: changed expectations are updated, dropped
   scenarios deleted, everything else stays untouched and green.

There is no path that changes behavior without passing through the
specification. The day a fix skips it, the specification stops being the
truth, and within months the team maintains code again with a folder of stale
documents beside it.

## Under pressure

Production is failing and someone says "just patch it, we fix the spec later".
Later does not come. Say so to the person asking, in a sentence: once the code
moves without it, the specification no longer says what the system does, and
nobody returns to it once the fire is out. Do not offer a code-only fix. Offer the urgent path:
[references/urgent-path.md](references/urgent-path.md). It keeps the order and takes minutes: the
smallest specification edit, a failing test, the fix, one change set, one
reviewer.

If the code is simply wrong against a correct specification (outcome 1), no
specification edit is needed at all. Say so: it is the fastest case, not an
exception to the rule, and it takes the light path. A foreign-key constraint
for a relationship the entity model states is the one exception: it takes the
destructive path of the schema procedure, with the owner's yes (The
foreign-key exception), however urgent the fix.

## Workflow

1. Restate the report as an element of a use case.
2. Read that use case, the rows on its `requirements` list, and the entities it
   names. If no specification describes the behavior, check whether the system
   already has it; if so, follow the section above before classifying.
3. Classify with the sign-off test. State the outcome and why.
4. Run `impact.py` for the identifiers and nouns involved.
5. For outcomes 2, 4, 5: ask the owner to confirm the classification and the
   decision. For outcome 6: confirm it is in scope.
6. For a defect (1, 2, 4): describe the failing test that reproduces it, named
   after the use case and the element (a rule, a flow, a step, a precondition
   or a postcondition). If no element fits, it is not outcome 1, except a
   foreign-key constraint added later for a relationship the entity model
   states, which takes the destructive path of the schema procedure with the
   owner's yes (The foreign-key exception). For any other outcome 1, hand
   over on the light path with the note `Fixes: UC-XXX <element>` for the
   commit; no change record.
7. For outcomes 2, 4, 5 and 6, write the change record from [templates/change-record.md](templates/change-record.md), with the
   differences from today when the behavior already exists, and save it as
   `docs/change-records/UC-XXX-<kebab-name>.md`: the review, the
   implementation and its gate read it there, and the pull request links it. When the change starts from an entry of a recovery change log, the Report names it (`change log #3`), the entry's Decision becomes `in change: <this record's path>`, and its Use case column gains the change record's use case when it is not already there.
   Every decision the owner made goes into its decisions table with the
   element that carries it; when the specification is written, each decision
   has that element, and every flow and rule the change adds is mapped in the
   sources table to the request, a decision, today's behavior or a listed
   assumption. Then hand over to the next skill in the table. The record
   never copies a use case's Status; it names the reset (or none).
8. When the owner defers the change and the project uses the A-files, name the
   AHEAD item it becomes: a proposal that links the change record, without
   copying it (the pairing contract in the conventions).

## Validation

Before handing over:

- The classification names an outcome and an element (for a foreign-key
  constraint, the relationship), with the reason.
- For anything but outcomes 1, 3 and 7, the specification change is described
  and the Status reset is stated.
- A change record exists for outcomes 2, 4, 5 and 6 only. For outcome 1 the
  hand-over names the failing test and the note `Fixes: UC-XXX <element>`;
  for a foreign-key constraint, the destructive path of the schema procedure
  with the owner's yes (The foreign-key exception).
- The impact list was produced, not assumed.
- For behavior the system already has: today's behavior was written down
  before the change, and every difference from today is in the record.
- No code was changed by this skill.

## Worked example

Report: "A member borrowed a sixth book."

Specification, `UC-002 BR-005`: *A member may have at most 5 open loans.*
Its Examples table has input `open loans before borrowing` and result rows
`4 → allowed`, `5 → refused`.

- Element: `UC-002 BR-005`, flow A2.
- Sign-off test: nobody wants six. The specification is clear and right.
- **Outcome 1, code wrong.** No specification edit.
- Impact: `UC-002` only; journey `TC-001` includes it; tests carry `UC002`.
- Failing test first: `br005_sixth_loan_is_refused` in the suite of `UC-002`,
  with five open loans, expecting refusal and no loan recorded.
- The light path, no change record: the fix through
  `up-7-implementing-use-cases UC-002`, the guard check of `UC-002 BR-005` if
  wanted, and the commit carries `Fixes: UC-002 BR-005`.

The same report with a different specification:

| The specification says | Outcome |
|---|---|
| "at most 5 open loans", examples given | 1, code wrong |
| "at most 5 loans" with no example, and renewals counted by some readers | 4, ambiguous: ask whether a renewed loan counts |
| "at most 6 open loans", and the library now wants 5 | 5, enhancement |
| Nothing about a limit | 5, enhancement; a rule and a flow are missing |
