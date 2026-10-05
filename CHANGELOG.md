# Changelog

All notable changes to upspec. Versions follow semantic versioning.

## 0.2.0

- Recovery: the change log is the alignment backlog. A new kind, Claimed but
  not built, holds what an old document promises and the code lacks; the
  decisions later, in change, aligned and dropped follow an entry, and only
  the coverage audit's report closes it. With the A-files, recovery drafts
  one AHEAD item per use case and writes them on the owner's yes.
- The ledger check refuses a dropped entry without its reason, an entry in
  change whose record is missing, and an aligned entry whose audit reports
  are missing or do not cover its use cases, and prints the backlog.
- The router prints the alignment count, hints when an entry is ready for
  its audit, and warns when an ability is done while its use cases still
  have open entries; it never blocks new work.
- Triage names the change log entry a change starts from and marks it in
  change; the audit lists the entries its report can close.

## 0.1.0

The first public release.

- Fourteen skills for specification-first development with use cases: a
  router that names the next step; project setup with rigor profiles and
  agent hooks; the requirements catalog; the entity model; the use case map;
  use case specifications; their review; implementation against an approved
  specification; tests derived from the specification; coverage audit;
  journeys across use cases; change triage; recovery of specifications from
  existing code; and splitting a specification set for several teams.
- Bundled scripts (Python 3.9 or later, standard library only) that validate
  specifications, read the project's state, check the finish of a change and
  audit coverage.
- Works alone or with the A-files in the same project.
