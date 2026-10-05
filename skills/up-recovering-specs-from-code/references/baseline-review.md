# The baseline review

Turns recovered drafts into the baseline from which all later change proceeds.
It needs two kinds of knowledge, usually two people.

## Contents

- Why two
- Preparing it
- Questions for the one who knows the system
- Questions for the one who knows the business
- What the review produces
- Working alone
- After the review

## Why two

| Reviewed only by | The result is |
|---|---|
| Someone who knows the code | A transcription of the code with better formatting |
| Someone who knows the business | A wish list that does not describe the running system |
| Both | The baseline |

## Preparing it

Hand over, per use case under review:

- the specification draft;
- its rows of the ledger (what came from where);
- its suspects, each with the question to answer;
- the entities it uses.

Keep the unit small: one use case per sitting, or one cluster of closely
related ones. Only suspects of kind `decide`, and claims an old document makes that the code never built, go on the agenda; `tidy` items go to whoever maintains the code.

The plan names sittings by use case id. It holds no counts and no Status
values: quote the counts the ledger check prints, and let each use case's
Status line speak for itself.

## Questions for the one who knows the system

For each flow, rule and state change:

1. Is this path reachable today? From which entry points?
2. Is this validation enforced on every way in, or is there a second entry
   that skips it?
3. Is this number a decision, or a leftover from something else?
4. Does anything else write this data that the specification does not
   mention?
5. What happens when this fails halfway? Is what the failure postcondition
   says really true?

They catch: the recovered flow that describes a path nothing reaches any
more; the check that exists but is bypassed; the rule inferred from a
constant that means nothing.

## Questions for the one who knows the business

1. Is this what the system is supposed to do? Would you sign it?
2. Is anything here accurate and indefensible?
3. What does the system not handle that happens in reality?
4. Do you still use this word in this sense?
5. Who relies on this behavior? Would anyone notice if it disappeared?

They catch: the flow that is true and wrong; the alternative nobody built and
nobody noticed; the noun the business stopped using years ago.

## What the review produces

**A baseline.** For each use case the review settled, Status moves from
`Draft` to `Reviewed`. `Approved` is the owner's to write on the Status line,
never yours, even after the owner says yes in the conversation: list the use
cases that are ready and leave the line to them. Because the
code exists and the ledger shows it, `Implemented` is then justified by a
coverage audit, not by assumption.

**A change log** for everything the review could not settle. Four kinds:

| Kind | What it is | Choices |
|---|---|---|
| Undocumented behavior someone depends on | In the code, never specified, and a real user would notice its absence | Specify and approve it, or deliberately drop it |
| Behavior that stopped working | A validation that no longer fires, a flow that errors out | The specification states what should happen; the gap is a defect |
| Two paths doing the same job differently | Two entry points, different rules | The business decides which is right; the other becomes a change |
| Claimed but not built | An old document promises behavior the code does not have; the evidence is the document's line | Build it later, or drop the claim with its reason |

A decision that leaves work, whatever the kind ("the other path becomes a
change", "filed as a defect"), is written `later: <the decision>`, so no
work hides in free text; `dropped: <reason>` closes an entry without work.
When a change takes an entry up, triage writes `in change: <change record
path>` into it. An entry closes only on the audit's report: once the
coverage audit of each of its use cases comes back without gaps, whoever
acts on the reports writes `aligned: <report>` (one per use case,
separated by `;`); each cited report must list the entry on its `Change log`
line. The audit itself writes nothing but its report, and a Status is never enough: a defect fixed against a correct specification
leaves the Status where it was.
The router keeps an aligned entry open, with a warning, while its reports fail the shared closure check.

Each entry is classified with the sign-off test (would a stakeholder have
signed off the specification as it stands, knowing what they want now?),
decided by stakeholders, and recorded. From here each one goes through
`up-triaging-change-requests` like any other change.

Nothing is quietly fixed on the way through the review.

## Working alone

If one person holds both kinds of knowledge, split the review anyway:

1. A pass with the system questions only, with the code open.
2. A separate pass with the business questions only, with the code closed,
   reading the specification as a stakeholder would. A fresh context that
   receives only the specification and the business questions does this well.
3. For every item you cannot answer from knowledge, name who can. If nobody
   can, it stays open in the change log; do not decide it by guess.

## After the review

The system now runs the same specification-first loop as a new one. Before
the first change to a recovered use case, tests pin its current behavior.

The entries decided `later` are the alignment backlog. They wait beside new
work and are taken up one change at a time, through triage like any other
change; nothing about them has to be done before new work starts.

**With the A-files, hand the backlog over.** Draft one AHEAD item per use
case that has `later` entries, and one for each `later` entry with no use
case:

- title "Align UC-XXX <name> with the code"; Kind `proposal`; State `open`;
  Ability: the one whose `Specs` line names the use case, or empty;
- **What:** the entries by number ("change log #3, #9"), not their content;
- **Why:** the baseline review and its date; **Write-up:** the change log.

Show every draft at once and write nothing until the owner says yes; the
owner may edit or merge drafts first. On the yes, write the items and put
each item's identifier in the `Ahead` column of its entries. A rejected
draft leaves its entries `later` without an item; the router reports them.
In a later round of recovery, draft only for `later` entries with an empty
`Ahead`, and propose adding an entry to its use case's open item rather than
a new one. A dropped entry stays in the change log with its reason; when
every entry an item cites is dropped, the item is dropped in `AHEAD.md`.

The list this review produces is often the first time in years that anyone
knows what the system does. Treat it as a result in its own right.
