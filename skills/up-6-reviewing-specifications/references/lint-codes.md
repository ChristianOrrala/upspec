# Lint codes

`scripts/spec_lint.py` prints one line per finding:

```text
docs/use_cases/UC-004-book-room.md:12: ERROR DANGLING_REF [UC-004]: requirement FR-019 is not in the catalog
```

`path:line: SEVERITY CODE [element]: message`. Line 0 means the whole file.
Exit code 0 when clean, 1 on any error (with `--strict` also on any warning),
2 on a usage error, 5 on `OLD_FORMAT`.

## Contents

- Format codes
- Retired codes
- Cross-file codes
- Per-file codes
- Options
- The baseline

## Format codes

| Code | Meaning |
|---|---|
| `OLD_FORMAT` | Earlier formats detected; stop with exit 5 and use `up-migrating-spec-formats` |
| `FRONT_MATTER` | Missing or malformed front matter, unsupported YAML or a missing required key |
| `STALE_OVERVIEW` | The generated overview differs from the use case files; regenerate it |
| `STUB` | A stub whose `status` is past Draft |
| `EXAMPLES_FORM` | A rule needs a filled Examples table: a blank line before the Examples table, input columns then final `result`, and rows on both sides of each boundary |
| `GHERKIN_FORM` | A journey needs one gherkin block, one named Scenario, allowed steps and comments matching its `use_cases` list |
| `ENTITY_TYPE` | An attribute type is outside the closed business list |
| `REFERENCE_NO_RELATIONSHIP` | A Reference to ENTITY lacks a relationship in the diagram |
| `NEED_FORM` | A functional row lacks Role or Need, or a Statement follows no EARS pattern |
| `RECORD_FORM` | A change record lacks a required section or has an unknown outcome |
| `UNREADABLE` | A file cannot be read |

## Retired codes

Retired codes: `NO_START_END`, `NO_SYSTEM`, `LABEL_FORM`, `ACTOR_UNCONNECTED`,
`USE_CASE_UNCONNECTED`, `SPEC_NOT_IN_DIAGRAM`, `NAME_MISMATCH`, `SPEC_PENDING`,
`FK_NO_RELATIONSHIP`, `STORY_FORM`. The overview is generated from existing
files; references use business types, and functional rows use Role and Need.

## Cross-file codes

| Severity | Code | Meaning | Fixed by |
|---|---|---|---|
| ERROR | `DUPLICATE_ID` | A use case, journey or requirement identifier used twice | The owning skill |
| ERROR | `DANGLING_REF` | A requirement id on a `requirements` list, a `UC-XXX BR-YYY` citation, a use case link or a process link that points to nothing | The owning skill |
| ERROR | `STATUS_INVALID` | A Status outside the allowed values | The owning skill |
| ERROR | `UNREADABLE` | A file that cannot be read | — |
| WARN | `FR_UNREALIZED` | A functional requirement in scope that no use case links (INFO while some use cases are Draft stubs) | up-5-writing-use-case-specs |
| WARN | `REQ_STATUS_DRIFT` | A requirement's progress Status differs from what its use cases imply | up-2-cataloging-requirements |
| WARN | `RULE_COPIED` | The same rule text in two use cases | up-5-writing-use-case-specs: keep one, cite it |
| WARN | `AVOIDED_WORD` | A word the entity model lists under `Not:` | The owning skill |
| WARN | `RULE_RETIRED_CITED` | A use case cites a rule another use case has retired | up-5-writing-use-case-specs: cite the rule that replaced it |
| WARN | `LABEL_MOVED` | A flow or rule name sits under another label than in the last commit (only under git): labels never move | up-5-writing-use-case-specs |
| WARN | `DEAD_LINK` | A relative link in a specification file, the vision, the catalog, the entity model or a recovery record that leads nowhere | The owning skill |
| INFO | `UC_UNUSED_BY_TC` | Journey test cases exist, none includes this use case | up-writing-journey-test-cases |
| INFO | `EXTERNAL_REF` | A citation into another bounded context (`billing/UC-003 BR-002`); it is not checked here | The cross-context review |
| INFO | `SPELLING` | An older file or folder spelling is in use | — |
| INFO | `BASELINE_STALE` | A baseline entry no longer matches a finding | Refresh the baseline |
| INFO | `CATALOG_PENDING` | The guideline file's rules block expects `docs/requirements.md`, which is not written and not recorded as skipped | up-2-cataloging-requirements, or record the skip |

## Per-file codes

Every use case file is also checked on its own.

| Severity | Code | Meaning |
|---|---|---|
| ERROR | `TITLE_MISSING`, `SECTION_MISSING` | The file lacks its title, a required section or required front matter (reported as `FRONT_MATTER`) |
| ERROR | `ID_FORMAT`, `STATUS_INVALID` | Identifier or Status outside the convention |
| ERROR | `RULE_UNDEFINED` | A step cites a rule this use case does not define |
| ERROR | `FLOW_ANCHOR_INVALID`, `CONTINUE_INVALID` | A flow names or continues at a step that does not exist |
| WARN | `STEP_NUMBERING`, `STEP_COUNT` | Steps not numbered from 1, or outside three to nine |
| WARN | `STEP_ACTOR`, `STEP_IF`, `CHECKS_WHETHER` | A step that does not start with who acts, branches, or checks instead of validating |
| WARN | `VALIDATION_UNANSWERED` | A validating step no flow is anchored to |
| WARN | `FLOW_LABEL`, `FLOW_TRIGGER`, `FLOW_ANCHOR`, `FLOW_EMPTY`, `FLOW_ENDING` | A flow without label, trigger, step anchor (`(step N)` or `(A2 step N)`), steps or one of the two endings |
| WARN | `NO_ALTERNATIVE_FLOWS` | An empty section without the italic statement that nothing can fail |
| WARN | `POSTCONDITIONS_EMPTY`, `POSTCONDITION_REACTION` | A missing postcondition list, or a failure postcondition that is a reaction |
| WARN | `RULE_NUMBERING`, `RULE_UNCITED`, `RULE_EMPTY` | Rules not numbered from 001, cited nowhere, or without text (a retired rule needs one line saying where it went) |
| WARN | `RULE_RETIRED_CITED` | A step cites a rule of this use case that is retired |
| WARN | `WEAK_WORD`, `MECHANISM_TERM` | A word that leaves a decision open, or says how the system is built |
| WARN | `IMPLEMENTATION_DETAIL` | An internal name (`needs_human_assist`), a code span or a millisecond figure: the specification transcribes the code |
| WARN | `SPEC_SIZE` | More than 500 lines, 24 alternative flows or 30 rules: too large to skim or review |
| INFO | `SPEC_SIZE` | More than 250 lines, 12 alternative flows or 15 rules: still reviewable; check the goal level |
| WARN | `SCREEN_COPY` | An emoji in the text: screen copy, not what the message tells the actor |
| INFO | `SCREEN_COPY` | A quotation of more than 12 words: quote exact screen words only where a rule depends on them |
| WARN | `FILE_NAME`, `TRIGGER_MISSING`, `REQUIREMENTS_LINE`, `PRIMARY_ACTOR_SYSTEM` | File name, trigger, requirement list or primary actor outside the convention |
| INFO | `UI_DETAIL` | Screen vocabulary in a step |
| INFO | `RULE_BOUNDARY` | A quantity or date without boundary examples |
| INFO | `VALIDATION_MULTI` | One validation answered by several flows |
| INFO | `MECHANISM_TERM` | A mechanism word that the entity model defines as a business noun |

All per-file findings are fixed by `up-5-writing-use-case-specs`.

## Options

| Option | Effect |
|---|---|
| `--docs DIR` | Documentation folder (default `docs`) |
| `--only ID` | Only findings about this identifier or file |
| `--strict` | Fail on warnings too |
| `--format json` | Findings and summary as JSON |
| `--trace` | The traceability matrix instead of findings |
| `--baseline FILE` | Use this baseline (default `DIR/.spec-lint-baseline.json` when present) |
| `--no-baseline` | Report every finding |
| `--update-baseline` | Accept all current errors and warnings, then exit 0 |

## The baseline

For a project that adopts the lint with existing findings.
`--update-baseline` writes the current errors and warnings to
`docs/.spec-lint-baseline.json`; from then on only new findings are reported.
An entry is keyed by code, file, element and message, not by line, so it
survives edits elsewhere in the file. Entries that stop matching are reported
as `BASELINE_STALE`.

The baseline is a decision of the owner. Do not update it during a review
unless asked.
