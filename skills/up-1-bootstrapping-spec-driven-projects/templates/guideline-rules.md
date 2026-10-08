## Working from specifications

**Profile:** [solo | team]

The specifications under `docs/` are the source of truth for what this system does. Code follows them.

1. **Read before deciding.** Before changing behavior, read the use case in `docs/use_cases/`, the rows it links in `docs/requirements.md`, and the entities it names in `docs/entity_model.md`.
2. **Name the use case.** Every instruction, commit subject and pull request names the use case it works on, for example `UC-012: allow team leads to assign inactive users`.
3. **Specification first.** A behavior change starts as a change to the specification. Code that changes behavior without one is not accepted. A change without a behavior change says so on its own line, naming the use case it stays within or `none`: `No behavior change: UC-012`.
4. **Not before approval.** Do not implement a use case whose Status is `Draft` or `Reviewed`. Agents never set `Approved` or `Done`; a person does.
5. **Stay inside the use case.** Change only what the named use case requires. Anything else you find goes on a list for the owner, not into the change.
6. **Synchronize, do not regenerate.** When a specification changes, change only the code and tests its changed elements touch.
7. **Do not decide silently.** Where the specification leaves something open, list what you decided with each change (the invention list). If it concerns behavior a user can observe, stop and ask.
8. **Observable behavior only.** Specifications describe what actors do and what the system answers. Technical choices live in this file or in `docs/decisions/`.
9. **Identifiers are permanent.** Never reuse or renumber an identifier. Code that enforces a business rule carries `UC-XXX BR-YYY: <rule>` above it; tests carry the use case id and name the flow or rule they cover.
10. **Status follows evidence.** Change a `status` field only when the evidence for that step exists: a clean validator for `Reviewed`, merged code with markers for `Implemented`, passing tests for every flow and rule for `Tested`.

Where skills for specification-first work are installed, start with the one that matches the task, even when the task looks simple: implementing or synchronizing a use case goes through `up-7-implementing-use-cases` (its finish check runs before the code and before the report), tests through `up-8-deriving-use-case-tests` (its guard check proves each test), a bug report or a change request through `up-triaging-change-requests`, which classifies it against the specification before any code is read.

<!-- Stack rules (languages, frameworks, commands, naming) belong in their own section of this file, not in this one. -->
