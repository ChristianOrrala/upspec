# Context Map

Which bounded contexts exist, what each owns, and what crosses between them.

## Contexts

| Context | Business capability | Owner | Use cases | Entities | Folder or repository |
|---|---|---|---|---|---|
| [workshop] | [Booking and carrying out repairs] | [team or person] | [UC-001 to UC-017] | [CUSTOMER, BIKE, WORK_ORDER] | [workshop/] |
| [billing] | [Invoicing and payments] | [team or person] | [UC-018 to UC-030] | [INVOICE, PAYMENT] | [billing/] |

New identifiers in every context start above: [UC-030, FR-024, TC-006]

## Contracts

One row per thing that crosses a boundary. The provider owns the contract and
agrees every change with its consumers first.

| Contract | Provider | Consumers | What it states | Key | Attributes a consumer may rely on |
|---|---|---|---|---|---|
| [Work order completed] | [workshop] | [billing] | [A repair is finished and may be invoiced] | [work order number] | [customer, agreed amount, completion day] |

## Shared Journeys

| Journey test case | Contexts | Owner |
|---|---|---|
| [TC-004 Repair Paid] | [workshop, billing] | [billing] |

## System-wide Requirements

| Requirement | Home | Owner | Cited as |
|---|---|---|---|
| [NFR-001 Retention Period] | [platform] | [person] | [platform/NFR-001] |

## Cross-context Review

**Who:** [person or group]
**Rhythm:** [for example every two weeks, and whenever a contract changes]

## Decisions

| Date | Decision | Reason |
|---|---|---|
| [date] | [Split into workshop and billing] | [Measured clusters; weekly conflicts under docs/] |
