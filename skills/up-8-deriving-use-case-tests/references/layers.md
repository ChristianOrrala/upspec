# Test layers

Where the tests of a use case run. The choice follows from how the use case is
reached, not from habit.

## Layers, from cheapest to most expensive

| Layer | Runs | Good for | Typical amount |
|---|---|---|---|
| Static checks | Without executing anything | Project-wide rules: layering, forbidden dependencies, formatting | All code |
| Rule tests | One rule in isolation, no infrastructure | Business rules and their boundaries | One or two per rule |
| Integration tests | Behavior with real dependencies (a real database, real collaborators) | A whole flow of a use case without an interface; persistence, transactions, constraints | One per path of the use case |
| Interface tests without a browser | The full flow from the interface down to stored state, driven in-process | Use cases with a user interface, where the stack offers this level | One per path of the use case |
| Browser tests | A real browser against the running system | Only what exists in a browser: rendering, keyboard, downloads, browser-specific behavior | Few, selective |
| Journey tests | Several use cases in sequence | State passed between use cases | One per journey test case |

The wide middle is where most of a use case is covered: the layers that
exercise real behavior with real dependencies at moderate cost. Rule tests
keep boundaries cheap to check. Browser tests are slow and fragile; spend them
where the browser itself is the subject.

## Choosing for one use case

1. Does the use case have a user interface?
   - Yes, and the stack can drive the interface without a browser: that level
     is the primary test for every path.
   - Yes, and it cannot: integration tests below the interface for every path,
     plus a small number of browser tests for the paths where the interface's
     own behavior matters.
   - No: integration tests for every path.
2. For each business rule: a rule test at the boundary, unless the primary
   test already asserts both sides of the boundary cheaply.
3. For each linked non-functional requirement: use the verification method the
   catalog names. Do not disguise a load test as a unit test.

The specification tells you which case applies. Decide once per use case, not
per test.

## Detail and seams

Tests of one use case own the detail: every alternative flow, every message's
content, every displayed item. Journey tests own the seams: state flowing from
one use case into the next. A journey test that re-asserts the columns of a
list is testing at the wrong level, and a use case test that walks through
three use cases is a journey.

## Where test-first fits

The specification comes first in every case. Inside that:

| What you are building | Order |
|---|---|
| A business rule | Failing test from the rule, minimal code, refactor |
| A service or an interface between systems | Test that fixes accepted input, expected output and error representation, then code |
| A user interface | Specify the observable behavior, build the interface, then write the tests. Tests written before the interface exists assume components and layout that are not decided and get rewritten |

## Real dependencies

Tests that mock the thing whose behavior they claim to verify prove little. A
use case whose postcondition is "a work order exists" is verified against the
store the project really uses, in a disposable instance. Mock what is outside
the system: the secondary actors.

For a secondary actor, test both that the system calls it as the step says
and what the system does when it refuses or does not answer, if a flow covers
that.

## What does not belong in a use case's tests

- Assertions about internal calls, queries or structure.
- Coverage of code paths no unit of the specification describes. If such a
  path matters, the specification is missing something: report it.
- Performance thresholds measured on a developer machine and reported as
  verified.
