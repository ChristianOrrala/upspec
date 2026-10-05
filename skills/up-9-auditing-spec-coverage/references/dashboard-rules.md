# Dashboard rules

What each cell of the spec dashboard means and why it is computed that way.

## Contents

- The question the dashboard answers
- Table 1: progress
- Table 2: one row per use case
- Status vocabulary on a board
- Requirement Status
- Limits of the dashboard
- Reading it

## The question the dashboard answers

Not "did we finish the tasks" but "is the intended behavior specified,
implemented and verified". Closed tickets and counted story points show
activity. They say nothing about whether specification, code and tests still
fit together.

## Table 1: progress

| Row | Complete | In progress | Not started |
|---|---|---|---|
| Functional requirements | Every use case that links it is `Tested` or `Done` | Linked, but not all of those use cases are there yet | No use case links it |
| Use cases | Status `Tested` or `Done` | Has a specification below that Status | In the diagram without a specification |
| Use cases with full test coverage | Main scenario, every alternative flow and every business rule is named by a test | Some are | None is |
| Regression stability | From the test report: all tests pass | — | — |

Coverage is the share that is complete. `Deferred` and `Rejected`
requirements and `Obsolete` use cases are left out of the totals.

A requirement is not complete because a ticket was closed. It is complete when
its intent is expressed in an approved use case, that use case is implemented,
and derived tests verify it.

## Table 2: one row per use case

| Column | Value | Rule |
|---|---|---|
| Linked FR | Identifiers | From the Requirements line |
| Status | As in the file | Never changed by the dashboard |
| Code | yes / no | A file outside the docs and test folders carries the use case id |
| Unit | yes / partial / no | Tests name the main scenario, every flow and every rule; some; none |
| E2E | yes / planned / no | A journey test case with Status `Automated` includes the use case; a journey includes it but is not automated; none |
| Regression | yes / no / unknown | The test report has no failures; has failures; no report was given |
| Integrity | Strong / Partial / Weak | See below |

**Integrity** says how well intent, code and verification fit together for
that use case:

- **Strong:** Status is `Approved` or later, and Code, Unit and E2E are all
  yes, and nothing regressed.
- **Weak:** none of Code, Unit and E2E has any evidence.
- **Partial:** everything in between.

A use case with code and no approved specification is never Strong, however
many tests it has: nobody agreed on what it should do.

## Status vocabulary on a board

A board is a view of the Status field. If older material or a tool uses other
column names, map them:

| Board column | Status |
|---|---|
| Draft | `Draft` |
| Review | `Reviewed` |
| Approved | `Approved` |
| Implemented | `Implemented` |
| Verified | `Tested` |
| Deployed | `Done` |

The use case is the unit of flow. It moves when its evidence exists, not when
a time box ends.

## Requirement Status

Stored in the catalog, derived from use cases:

| Status | When |
|---|---|
| Open | No linking use case is `Implemented` yet |
| In Progress | Some are `Implemented` or later, others not |
| Implemented | All are `Implemented`, `Tested` or `Done` |
| Verified | All are `Tested` or `Done` |

If the stored Status differs, the specification lint reports it; the catalog
skill updates it. The dashboard shows the derived view regardless.

## Limits of the dashboard

- It counts markers. A marker is a claim that a test or a piece of code
  belongs to a unit. The audit of a use case checks the claim.
- "Unit: yes" does not mean the tests are good. The guard check in the test
  skill shows whether a test fails when its rule is broken.
- Regression stability needs a test report in JUnit XML. Without one the cell
  says unknown. It is never assumed.
- A project that names its tests without use case ids shows "no" everywhere.
  That is a traceability gap worth closing, not a dashboard error.

## Reading it

| Pattern | Likely meaning | Look at |
|---|---|---|
| Code yes, Status `Draft` or `Reviewed` | Built before it was approved | The review; whether the specification was written after the code |
| Status `Tested`, Unit partial | Status moved without evidence | The coverage audit of that use case |
| Unit yes, E2E no on a use case that hands state to another | The seam is untested | A journey test case |
| Many use cases not specified | The diagram is ahead of the specifications | Delivery order |
| Regression "no" after one use case changed | The change broke a neighbor | The failing tests name the use case |
