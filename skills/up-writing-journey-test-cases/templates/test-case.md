# Test Case: [Journey Name]

## Overview

**ID:** TC-XXX  
**Goal:** [One sentence: who does what across the journey, and which outcome is verified end to end]  
**Priority:** [Critical | High | Medium | Low]  
**Status:** Draft

## Roles

- [Role (what it does in this journey)]
- [Second role, if the journey passes between roles]

## Preconditions

- [Data that must exist before the journey starts, with literal values (where it is seeded from)]

## Flow

| Step | Name | Description | Test Data | Use Case |
|------|------|-------------|-----------|----------|
| 1 | [Do something] | [What the role does and what the system shows] | [Literal values] | [UC-XXX](../use_cases/UC-XXX-name.md) |
| 2 | [Verify ...] | [Observable result the next step depends on] | - | - |
| 3 | [Do the next thing] | [Operates on what step 1 created] | [Literal values or -] | [UC-YYY](../use_cases/UC-YYY-name.md) |

## Validation

1. **[Check name]**: [End-state expectation, observable after the flow]
2. **[Check name]**: [Second expectation]

## Postconditions

- [Each record the journey creates or changes, with its literal values]
- [Order in which records must be removed, if one depends on another; seeded data stays]
