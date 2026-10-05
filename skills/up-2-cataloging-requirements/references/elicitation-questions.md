# Elicitation questions

For the case with no workshop and no transcript: one person with an idea, or
material that leaves obvious holes. Ask what is missing, not everything.

## How to ask

- Read what exists first. Never ask for something the material already says.
- A few questions per turn, the most consequential first. Scope before
  quality, quality before detail.
- Offer a concrete default when one is common, and say it is a default.
- An answer of "I don't know yet" is a ledger entry of kind Undecided, not a
  reason to guess.
- Stop when every role has at least one goal, the boundary is drawn, and every
  quality wish either has a number or sits in the ledger.

## By gap

**No roles named.**
- Who uses this, and what does each of them come to do?
- Does anything act on a schedule or arrive from another system?

**Goals named, benefits missing.**
- For each goal: what is better for that role once it works? The benefit is the
  "so that" and often reveals the real requirement.

**No boundary.**
- What will this deliberately not do, even though someone might expect it?
- Which neighboring system or manual step stays as it is?

**Quality stated as an adjective** (fast, secure, reliable, easy).
- Fast: how many seconds, for which action, under how many concurrent users?
- Secure: who must not see or change what? Which data is personal or
  confidential?
- Reliable: how long may it be unavailable, and when?
- For each answer: how would we check it? (This fills the Verification column.)

**No limits mentioned.**
- Is the platform, language, hosting or database fixed?
- Is there a deadline or a budget that shapes scope?
- Which laws, standards or company policies apply? Which article or section?

**Data.**
- Which things does the system have to remember about each role's work? (These
  become entities; note the nouns, do not design tables.)
- How long may data be kept, and who may ask for it to be removed?

## Stakeholders who are not users

Ask this for every functional requirement once the rows exist:

| Stakeholder | Typical interest | Becomes |
|---|---|---|
| The business | Nothing of value leaves without being recorded or paid | Constraint, or a rule noted for the use case |
| A regulator | A procedure can be shown to have been followed | Constraint with a source |
| An auditor | Who did what and when can be reconstructed | NFR in category Security |
| Operations | A failure halfway leaves a state someone can recover | NFR in category Availability or Maintainability |
| Other customers | One user's action does not block or expose another | Constraint or NFR |

A use case typically has two to five stakeholders. If the answer for a
requirement is "only the user", ask once more who pays when it goes wrong.

## Consolidating a transcript

1. Mark each statement with its speaker or source.
2. Collapse repetition, keep disagreement. Two people saying different numbers
   is one ledger entry, not one row with the later number.
3. Separate what was decided from what was wished and from what was asked.
   Questions that were left unanswered are ledger entries.
4. Keep the business's own nouns exactly as spoken. If two words were used for
   what may be one thing, add a ledger entry of kind Suspected duplicate;
   settling the vocabulary is the entity model's job.
