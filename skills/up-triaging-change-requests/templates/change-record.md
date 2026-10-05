## Change record: [short title]

**Report:** [who reported what, in one or two sentences; or the recovery change log entry it starts from, "change log #3"]
**Element:** [UC-XXX step N | UC-XXX A1 | UC-XXX BR-00N | no use case covers it]

### Classification

**Outcome:** [1 code wrong | 2 specification wrong | 3 test wrong | 4 specification ambiguous | 5 enhancement | 6 new use case | 7 no behavior change]
**Sign-off test:** [Would a stakeholder have signed off the specification as it stands, knowing what they want now? yes / no, because ...]
**Decided by:** [name or role, for outcomes 2, 4, 5, 6]

### Owner's decisions

[Every decision the owner made for this change, one row each, with the element of the specification that carries it. A decision kept only here is lost to the implementation; the implementer's finish check refuses one with no element.]

| # | Decision | Decided by | Lives in |
|---|---|---|---|
| [1] | [what was decided] | [owner, date] | [UC-XXX BR-00N / UC-XXX step N / UC-XXX A1 / out of scope / open] |

### Sources of new behavior

[When the change adds behavior: every flow and rule it adds, and what it rests on. Source is `the request`, `decision N` (a row of the owner's decisions), `today` (behavior the system already has) or `assumption N` (a row below). The implementer's finish check flags a flow or rule with no source: it is an invention.]

| Element | Source |
|---|---|
| [UC-XXX A1 / UC-XXX BR-00N] | [the request / decision 1 / today / assumption 1] |

### Assumptions

[What nobody decided and the specification still needed, for the owner to confirm. Each one names the element that rests on it.]

| # | Assumption | Element |
|---|---|---|
| [1] | [what was assumed] | [UC-XXX BR-00N] |

### Specification change

[None: the specification is right as it stands.]
[Or: what changes in which element, in one or two sentences. Status of UC-XXX goes back to Reviewed.]

### Differences from today

[Only when the system already has the behavior. One row per element that changes. Requested by names the request or the owner's decision; a row nobody requested is an invention and needs the owner's yes before it stays. Seen in says how today's behavior is known: `code` (read from the code: pin it with a test before anything changes), `test <name>` (pinned by that test), or `observed` (seen on the running system with its real services; a test with a stand-in for an outside service pins only our side).]

| Element | Today | After the change | Requested by | Seen in |
|---|---|---|---|---|
| [UC-XXX step N / A1 / BR-00N] | [what the system does now] | [what it will do] | [the request / owner, date] | [code / test <name> / observed] |

### Impact

| Direction | Affected | What to do |
|---|---|---|
| Upward | [FR-XXX, vision scope] | [unchanged / row updated] |
| Sideways | [UC-YYY cites UC-XXX BR-00N] | [review that use case] |
| Downward | [TC-XXX, tests of UC-XXX, entity model] | [update test data / synchronize / schema change] |

### Reproduction

[For a defect: the failing test, named after the flow or rule, with its literal data and expected outcome.]

### Urgent path

[Not used. | Used: mitigation taken, who approved the specification edit, follow-up opened.]

### Next

[When the table has rows seen in `code`, first: pin each with a test that passes against today's code, write the test's name into its row, and commit the pins before any code changes. Tests of the new behavior come after the pins. Then the skill and the use case: for example `up-7-implementing-use-cases UC-XXX`.]
