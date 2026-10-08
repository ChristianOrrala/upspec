---
id: [TC-XXX]
goal: [Who does what and which end-to-end outcome is verified]
priority: High
status: Draft
use_cases: [UC-XXX, UC-YYY]
process: [../processes/name.bpmn]
---
# [Journey Name]

## Roles

- [Role and what it does in this journey]
- [Second role and what it does]

## Preconditions

- [Seeded data with literal values and its source]

```gherkin
Scenario: [Journey outcome]
  Given [starting state with literal test data in quotes]
  # UC-XXX
  When [first role performs the first use case with quoted literal data]
  Then [observable result carried to the next use case]
  # UC-YYY
  When [next role performs the next use case]
  Then [the journey's final observable outcome]
  And [another end-state expectation]
```

## Postconditions

- [Records created or changed, with literal values]
- [Cleanup order; seeded data stays]
