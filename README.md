# upspec

Stack-neutral skills for specification-first development with use cases.

**Status: 0.2.0.** All fourteen skills are built. Their scripts are tested against fixture
projects, and the skills are evaluated against sessions without them.

The full guide (installing, concepts, workflows, the checks, troubleshooting) is
[MANUAL.md](MANUAL.md).

## Skills

| Skill | Purpose |
|---|---|
| `up-0-navigating-spec-driven-work` | Where the project stands and what comes next |
| `up-1-bootstrapping-spec-driven-projects` | Rigor profile, docs tree, guideline rules, team instruments |
| `up-2-cataloging-requirements` | Requirements catalog and conflict ledger |
| `up-3-modeling-domain-entities` | Entity model as vocabulary, with lifecycles |
| `up-4-mapping-use-cases` | Which use cases exist, at the right level, in what order |
| `up-5-writing-use-case-specs` | One use case an agent can implement without inventing |
| `up-6-reviewing-specifications` | Lint and three-reader review, report only |
| `up-7-implementing-use-cases` | Implement or synchronize one approved use case |
| `up-8-deriving-use-case-tests` | Tests from the specification, proven to guard their rules |
| `up-writing-journey-test-cases` | End-to-end journeys across use cases |
| `up-triaging-change-requests` | Bug, change or hotfix as a specification-first change |
| `up-9-auditing-spec-coverage` | Coverage matrix and spec dashboard, report only |
| `up-recovering-specs-from-code` | Specifications for an existing system |
| `up-splitting-bounded-contexts` | Splitting a specification set for several teams |

## One set at a time

Seven of these skills answer requests that other spec-driven skill sets also
answer: requirements, the entity model, use case diagrams and specifications,
their review, test cases and recovery. With two such sets installed, both
respond to the same request. Use one set for those requests.

## How they fit together

```text
bootstrapping ─► vision (written by a person) ─► cataloging ─► modeling ─► mapping
                                                                              │
        ┌─────────────────────────────────────────────────────────────────────┘
        ▼
   writing ─► reviewing ─► approval (a person) ─► implementing ─► deriving tests ─► auditing
                                                                        │
                                                    journey test cases ◄┘

triaging turns every later request into a change that starts at the specification.
recovering brings an existing system to the same starting point.
splitting cuts a set that has outgrown review.
navigating tells you where you are in this picture.
```

Every skill name starts with `up-`, so typing `up-` lists them together. The
number that follows is the skill's place in the chain, from `up-1-` (set up)
to `up-9-` (audit); `up-0-` is the router. The four skills without a number
are side entries: journeys across use cases, triage of changes, recovery of an
existing system, and splitting a set that has grown too large.

Start with "set this repo up for spec-driven development" or "where are we
with the specs and what comes next?".

## Requirements

Python 3.9 or later for the bundled scripts (standard library only) and git.
Nothing is installed and nothing leaves the machine: the scripts read and
check files in the project.

## Credits

These skills are inspired by Simon Martinelli's work on the Unified Process.
They are an independent work, not affiliated with or endorsed by him.

MIT License. Copyright (c) 2026 Christian Orrala.
