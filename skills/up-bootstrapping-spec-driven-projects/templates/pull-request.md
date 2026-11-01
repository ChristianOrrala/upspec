## Use case

<!-- The identifier and name, for example UC-012 Assign Task. One use case per pull request. -->

## Kind of change

- [ ] New use case, or a new slice of one
- [ ] Changed behavior: the specification changes in this pull request
- [ ] Defect: the code did not do what the specification says
- [ ] No behavior change: add the declaration line the guideline file describes, below this list

## Specification

<!-- What changed in the specification, in one or two sentences, and who approved it. "Unchanged" for a defect or a change without behavior change. -->

## Invention list

<!-- Everything the specification left open and the implementation decided. One line each: what, where, kind (behavior, data, mechanism). "None" if nothing. A behavior item needs the owner's answer before merge. -->

## Evidence

- [ ] Validator and specification lint are clean
- [ ] Every flow and business rule of the slice has a test that names it
- [ ] The test suite passes
- [ ] Status in the specification matches this evidence

## Review order

1. The specification change: is this the behavior we want?
2. The invention list: is anything decided here that the owner should decide?
3. The code against the specification: does it do that, and only that?
4. The tests: is every flow and every rule exercised, on both sides of each boundary?
