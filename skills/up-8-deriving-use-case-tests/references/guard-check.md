# Guard check

Proof that a test fails when the behavior it claims to protect is broken. A
test that passes against broken code protects nothing, however plausible it
looks.

The check breaks code on purpose. Follow the steps exactly so that nothing
broken is left behind.

## Contents

- With the script
- Procedure by hand
- Every assertion, not only every test
- Rules
- What a weak test looks like
- When you cannot run it

## With the script

For each rule and flow, one command does the whole check and records it:

```bash
python3 scripts/guard_check.py "UC-012 BR-001" --file <the enforcing file> \
  --find "<the exact code that enforces it>" --replace "<the same code, broken>" \
  --test "<the project's command for the unit's tests>"
```

It runs the test on the code as it is (it must pass), applies the break, runs
the test again, always restores the file and checks that it is byte for byte
what it was, and appends the verdict to `docs/reviews/guard-checks.md`:
`caught`, `not caught` (fix the test, then run it again) or `invalid`. The
implementer's finish check accepts a rule as guarded only from that log, so a
break you reason about but do not run counts as not done.

Use the procedure by hand only when the break cannot be one replacement in one
file, and then say so in the report.

## Procedure by hand

For each rule test and each flow test:

1. **Start clean.** The working tree has no uncommitted changes:

   ```bash
   git status --porcelain
   ```

   If it prints anything, commit the work first, or stash it with
   `git stash push --include-untracked` and remember to restore it at the end.
   Do not start a guard check on top of uncommitted work.

2. **Break exactly one thing.** Find the code that enforces the rule (its
   marker comment `UC-XXX BR-YYY` points to it) and disable that one check:
   invert the condition, or make it always pass. Change nothing else. For a
   flow, disable the detection of its trigger.

3. **Run only the tests of that unit.** Use the project's own test command,
   narrowed to the suite or the test.

4. **Read the result.**

   | Result | Meaning |
   |---|---|
   | The unit's tests fail | They guard the rule. Note which assertion failed: the failure message names it |
   | The unit's tests pass | They do not guard it. Fix the test: usually it asserts a message but not the state, or its setup never reaches the boundary |
   | Other units' tests fail too | Fine; note it. They depend on the same rule |
   | Nothing can run | The break was too large (a syntax error, a removed function). Restore and make a smaller break |

5. **Restore.** Put the file back from version control:

   ```bash
   git checkout -- <the file you changed>
   ```

   Only the file you changed in step 2, by name. Never a blanket restore of
   the whole tree.

6. **Confirm clean.** `git status --porcelain` prints nothing again. If you
   stashed work in step 1, restore it now with `git stash pop`.

7. **Run the unit's tests once more.** They pass against the restored code.

Record the result per unit in the report: `guarded (by <the assertion that
failed>)`, `not guarded (fixed)`, or `not checked` with the reason.

## Every assertion, not only every test

A test with several assertions can be shown guarding while one of its
assertions checks nothing: the other assertions caught the break. Look at each
assertion that carries the rule, and ask which break would make that one fail.
If no single break can, it is vacuous. The usual causes:

- it runs after the screen, connection or resource it inspects is gone (after
  teardown, unmount or close), so it inspects nothing;
- it compares two values that the setup made equal;
- it inspects a copy taken before the action ran.

Rewrite a vacuous assertion against the state the rule protects, or delete it.
Report it either way.

## Rules

- One break at a time. Two broken rules at once tell you nothing about either.
- Never commit a break. Never leave the session with a broken file.
- Do not run the guard check against a shared environment or shared data. It
  runs where the unit tests run.
- If the project is not under version control, or its commands cannot be run
  where you work, copy the file before step 2 and copy it back in step 5, or
  run the whole check on a copy of the project. Compare the file with its
  copy afterwards, and say that you did it this way.
- A mutation testing tool, where the project already has one configured, does
  the same thing systematically. Use the project's configuration; do not
  introduce a tool for this.

## What a weak test looks like

| Symptom in the guard check | Usual cause | Repair |
|---|---|---|
| Passes with the rule disabled | Asserts that a message appeared; the state is never checked | Assert the postcondition |
| Passes with the rule disabled | Setup stays far from the boundary (3 of 8, never 8) | Use the rule's boundary examples |
| Passes with the flow's detection disabled | The trigger was never established; the test runs the main scenario | Establish the trigger in setup |
| Fails for an unrelated reason | The test depends on leftover data or on order | Make setup explicit and complete |
| Cannot be made to fail by any single break | The test asserts something no rule produces | Delete it or rewrite it against a unit |

## When you cannot run it

No test runner available, the suite needs infrastructure you do not have, or
the enforcing code cannot be located: say so per unit as `not checked` and
why. Do not report a unit as guarded on the strength of reading the test.
