# Process mode

Deriving journey test cases from a business process model in BPMN 2.0.

## Contents

- What the script reports
- Path rules
- Mapping activities to use cases
- From a path to a document
- Running it again
- Without the script

## What the script reports

```bash
python3 scripts/bpmn_paths.py docs/processes/order.bpmn
```

JSON with four parts:

| Part | Content |
|---|---|
| `lanes` | Lane name to the ids of its activities. A process without lanes has one lane named after the process |
| `activities` | Id, name, type, lane, and `ucId` when the name carries a use case id |
| `paths` | One entry per path: its ordered `steps` (activities, decisions, events), the `activities` on it, the `decisions` taken, and the name of its `end` |
| `warnings` | Constructs that were simplified or look wrong |

Exit code 0 on success, 1 when the file is not a usable process model, 2 on a
usage error, 4 when the file was refused.

**Refused files.** A file with a document type or entity declaration is not
parsed at all, because such declarations can make a parser read other files or
exhaust memory. Report it; do not work around it.

## Path rules

Applied in document order, the same way on every run:

| Construct | Rule |
|---|---|
| Exclusive, inclusive, event-based, complex gateway; several outgoing flows on any other node | Alternatives: each outgoing flow starts its own path. The decision is recorded with the gateway's name and the flow's name |
| Parallel gateway | All branches run. They are written one after another inside the same path, in document order, up to the joining parallel gateway. Alternatives inside a branch multiply the paths |
| Loop | A sequence flow is followed at most twice in one path: one path without the repetition, one with a single repetition |
| Node without outgoing flow | Ends the path |
| Sub-process | One step; its inside is not expanded. Reported as a warning |
| Boundary event | Not followed. Reported as a warning: model the alternative with a gateway if it should become a journey |

The number of paths is capped; when the cap is reached the script says so in
`warnings`. A process with that many paths is not a test plan anyone can
review. Split the process, or choose the paths that matter and write those.

## Mapping activities to use cases

Activities are tasks of any kind and call activities. Gateways and events are
not use cases.

1. If the activity's name contains a use case id (`UC-001 Place Order`,
   `Ship Order (UC-002)`), that is the use case.
2. Otherwise compare the name, ignoring case and extra spaces, with each
   specification's name.
3. Unmatched, or matched to an id that has no specification file: **stop.**
   Write no journey. List the unmatched activities with id, name and lane. The
   repair is a specification for the missing use case, or the id in the
   activity's name.

An activity that is really a step of a use case (too low) or a whole area of
work (too high) is a modeling problem. Say so; do not paper over it by mapping
it to the nearest use case.

## From a path to a document

| In the path | In the document |
|---|---|
| Activity | A When step preceded by its `# UC-XXX` comment |
| An activity visited twice (loop) | Two action steps |
| A decision | Nothing of its own. Quoted test data in an earlier step, or a Given step, must force it |
| Start and end events | The journey's goal and closing Then steps |
| Lanes of the path's activities | Roles |
| The model | The front matter `process` path |
| The path in words | A body description used to identify the journey on a rerun |

The `process` key links the model; the body description identifies its path:

```text
process: ../processes/order.bpmn

Path: Order received → Create Order → Stock available? no → Cancel Order → Order cancelled
```

Add Then assertions between actions exactly as in a hand-written journey.

**Forcing a decision.** "Stock available? no" needs a product without stock.
That is a precondition with a literal value and a seed source, or test data in
an earlier Gherkin step. A decision nothing forces makes the journey unreachable.

Name the file after the path's outcome: `TC-002-order-cancelled.md`.

## Running it again

Before assigning numbers, find the journeys whose front matter `process` key links
the same model.

| Situation | Do |
|---|---|
| The journey's path still exists, unchanged | Leave it |
| The path still exists, its steps changed | Update in place, same number and file; Status back to `Draft` |
| A path has no journey | New journey, next free number |
| A journey's path no longer exists | Status `Obsolete`. Keep the file |

Report what was created, updated and made obsolete. Never delete or renumber a
journey: automated tests and reports refer to its id.

## Without the script

Read the XML and apply the same rules by hand. Say that you did, and keep to
models small enough to enumerate reliably; for anything larger, ask for the
paths that matter.
