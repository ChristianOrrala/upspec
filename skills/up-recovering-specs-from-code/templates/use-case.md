---
id: [UC-XXX]
name: [Use Case Name]
primary_actor: [Role that pursues the goal]
secondary_actors: [Supporting role or external system]
goal: [The outcome the actor walks away with, and why]
trigger: [The event that starts the use case]
status: Draft
requirements: [FR-XXX, NFR-XXX, C-XXX]
---
# [Use Case Name]

## Preconditions

- [A state already true before the use case starts, never checked inside it]

## Main Success Scenario

1. [Actor does something toward the goal.]
2. [System validates a condition (BR-001).]
3. [System records the result.]
4. [System confirms the result and shows what the actor needs.]

## Alternative Flows

### A1: [Condition Name]

**Trigger:** [What the system detected] (step 2)
**Flow:**

1. [System informs the actor of the condition and the next action.]
2. Use case continues at step 1.

## Postconditions

### Success Postconditions

- [What is true when the goal is achieved: every record created or changed]

### Failure Postconditions

- [What remains true on every unsuccessful end]

## Business Rules

### BR-001: [Rule Name]

[One decision, stated so that a test can decide pass or fail.]

| [input] | result |
|---|---|
| [value just inside the boundary] | [accepted outcome] |
| [value just outside the boundary] | [refused outcome] |
