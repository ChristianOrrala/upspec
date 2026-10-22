# Mechanical format mapping

Business types describe meaning, independent of storage.

| Earlier type or rule | Current type | Current rule |
|---|---|---|
| String | Text | Keep rules other than storage details |
| Integer | Number | Keep rules |
| Boolean | Yes/No | Keep rules |
| Date | Date | Keep rules |
| DateTime | Date and time | Keep rules |
| Primary Key | Identifier | Unique, never reused |
| Foreign Key (X.id) | Reference to X | Keep other rules; relationship stays in diagram |
| Values: A, B | Choice of A, B | Keep other rules |
| Decimal or Long without a key | Owner decides from meaning | Judgment item |
| Not Null | Unchanged type | Required |
| Length/Precision or Sequence | No type change | Drop storage detail |

The attribute Description column becomes Meaning. Data Type,
Length/Precision and Validation Rules become Type and Rules.

| Earlier record heading or field | Current location |
|---|---|
| Outcome: N … | front matter outcome: N; full classification text stays in Context |
| Element | front matter element |
| Decided by | front matter decided_by |
| Report and Classification's Sign-off test | Context |
| Owner's decisions | Decision; keep table |
| Specification change | Specification change |
| Differences from today and Impact | Consequences; keep both tables |
| Sources of new behavior, Assumptions, Reproduction, Urgent path | Same heading at level 2 when it has content |
| Next | Carry body verbatim into Consequences; list it for owner judgment |

Use case fields become front matter in order: id, name, primary_actor,
secondary_actors (when present), goal, trigger, status, requirements.
Journey fields become id, goal, priority, status, use_cases (unique in flow
order), process (link target only). The original Process line, including its
label and route, stays verbatim in the body. Their Flow and Validation remain
judgment. Functional requirement titles and benefits stay in Requirement
context outside the tables, for the owner to decide where they belong.

Unknown sections, duplicate headings and unplaced metadata leave the whole
file byte for byte, with a judgment entry. No conversion silently drops
instructions.

Installed copies share setup's classification and bundle baselines. Any
changed, undecided script holds back every script replacement and addition;
specification conversion continues. Resolve each through
`scaffold_docs.py --update` with `--replace` or `--keep`.
After all decisions, migration replaces untouched copies and adds the whole
missing set, including hooks, whenever `tools/specs/` exists. Setup's update
adds missing scripts only for an installed or requested set. Kept copies stay;
each script migration writes gets a fresh baseline in `upspec-installed.json`.
