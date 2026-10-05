# Use Case: [Use Case Name]

## Overview

**Use Case ID:** UC-XXX  
**Use Case Name:** [The actor's goal as a short verb phrase, exactly as in the diagram]  
**Primary Actor:** [Role that pursues the goal; several, comma-separated, only when each starts the use case alone for the same goal]  
**Secondary Actors:** [Supporting roles or external systems, comma-separated; delete the line when there are none]  
**Goal:** [One sentence: the outcome the actor walks away with, and why]  
**Trigger:** [The event that starts it: an actor's request, a point in time, a message from another system]  
**Status:** Draft  
**Requirements:** [FR-XXX, NFR-XXX, C-XXX](../requirements.md)

## Preconditions

- [A state that is already true before the use case starts and is never checked inside it]

## Main Success Scenario

1. [Actor does something toward the goal.]
2. [System validates that ... (BR-001).]
3. [System records ...]
4. [System confirms ... and shows ...]

## Alternative Flows

### A1: [The Condition as a Name]

**Trigger:** [What the system detected] (step N)  
**Flow:**

1. [System informs the actor of ... and shows ...]
2. Use case continues at step N.

## Postconditions

### Success Postconditions

- [What is true when the goal is achieved: every record created or changed]

### Failure Postconditions

- [What stays true on every unsuccessful end, for example: nothing is recorded and existing data is unchanged]

## Business Rules

### BR-001: [Rule Name]

[One decision, stated so that a test can decide pass or fail.]
Examples: [value just inside the limit: outcome. Value just outside: outcome.]
