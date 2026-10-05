## Tests of UC-XXX [Name]

Specification: `docs/use_cases/UC-XXX-<name>.md`, Status [Approved]
Layer: [interface without browser | integration | ...], suite `[path]`

| Unit | Test | Asserts | Guard check |
|---|---|---|---|
| Main | [test name] | [success postconditions] | [guarded] |
| A1 [name] | [test name] | [outcome; continues at step N / state unchanged] | [guarded / not guarded (fixed) / not checked: reason] |
| BR-001 [name] | [test name] | [inside the boundary: allowed; outside: refused] | |
| Pre-1 | [test name] | [cannot be entered without it] | |
| Post-F-1 | [covered by tests of A2, A3] | [state unchanged] | |
| NFR-XXX | — | [not measured here; verification method in the catalog: ...] | — |

### Changes to existing tests

| Test | Action | Why |
|---|---|---|
| [name] | [updated / deleted / untouched] | [the unit changed / was removed / is unchanged] |

### Gaps in the specification found while testing

- [UC-XXX BR-00N has a quantity and no boundary examples; the boundary was not assumed]

### Result

Suite: [n passed, n failed]. Working tree clean after guard checks: [yes].
Next: `up-9-auditing-spec-coverage UC-XXX`.
