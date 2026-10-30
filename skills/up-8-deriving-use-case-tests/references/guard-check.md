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

Any element of the use case can be checked, in the finish check's names:
`UC-012 BR-005`, `UC-012 A2`, `UC-012 Step 3`, `UC-012 Pre-1`,
`UC-012 Post-S-1`, `UC-012 Post-F-2`.

It runs the test on the code as it is (it must pass), applies the break, runs
the test again, always restores the file and checks that it is byte for byte
what it was. It reads the test's output, both streams together, and gives a
verdict about the break:

| Verdict | What happened | Then |
|---|---|---|
| `caught` | A test whose name holds both the use case and the element failed on an assertion | The test guards the element |
| `crashed` | The element's test stopped on an error rather than a failed assertion: a syntax error, a failed import, any exception the test did not expect (a bare `Error` or `Exception`, `StopIteration`, the project's own), a build that did not compile, or the runner marking the test as an error | The break proves nothing about the assertion. Make a smaller break that keeps the code running, or make the test assert the element's outcome before anything else can fail |
| `not caught` | The test still passed | Fix the test, then run the check again |
| `unclear` | The test failed, but the output does not say that the element's test failed on an assertion | Read the output the check prints: another element's test may have caught the break, the test's name may lack the use case or the element, or an error was printed apart from every test's report. Name a test after the element, or pass `--expect` |

Beside these four, `invalid` says the check proved nothing: the test failed
before the break, or ran past the time limit (`--timeout`, in seconds, 600 by
default). Fix the test or the command first.

**How the verdict is read.** Only lines that are new since the run before the
break count. The element's own report decides first: what the output shows
from the line that reports the element's test to the next test's report. That
part shows an error, or the runner marks the test as an error: `crashed`.
Otherwise `caught`, whatever another test printed, unless the output shows an
error apart from every test's report (before the first one, or under a
section of the whole run, as pytest's `--tb=line` prints it): then `unclear`,
because the output does not say whether the element's test crashed. Only when
no line reports the element's test does an error anywhere make the verdict
`crashed`. The explanation of a failed assertion is not an error: a pytest
diff line (`E           Loan`), a field labeled `Error:` and padded to a
column, as Go's testify prints a failed assertion (`Error:      Not equal:`),
or a line such as `Expected: 8`. An exception whose name does not end in
`Error` or `Exception` counts only on the line right after a traceback's
frame (`File "…", line 12` and its source line, or pytest's `>` line). For
`crashed` and `unclear` the check prints the new lines of the output, the
first 40 of them, and how many there were. With `--format json` the report
holds `element` (and `unit`, the same value under its earlier name), `file`,
`verdict`, `evidence`, `failed_test`, `log` and `restored`, and for `crashed`
and `unclear` the lines as `output` and their count as `output_lines`.

**What the name must hold.** Element numbers restart in every use case, so a
failed test counts only when the line that reports it holds both the use case
and the element, in a common spelling: `test_uc012_br005_...`,
`UC012Test.test_br005_...`, `testUc012Br005`, or a displayed name such as
`UC-012 BR-005 refuses a sixth loan`. A suite named after the use case with
tests named after their elements, as the conventions ask, usually prints both
on one line. A failing test of another use case's BR-005 does not count.

**`--expect TEXT`** serves a runner that prints no test names, or prints them
on separate lines: give the text that shows the element's test failed. The
break counts when that text appears more often after the break than before it,
and its part of the output is read as the element's report is: an error there
makes it `crashed`, otherwise it is `caught`.

**Which runners.** The signs the check reads follow the documented output of
common runners, named in the script as examples: unittest, pytest, Go, .NET,
Jest and Vitest, TAP, Mocha, RSpec, PHPUnit, JUnit with Maven or Gradle. The
package's own tests run only unittest, pytest and stand-in runners that print
the other shapes; Go's output with testify was captured from a real run by
hand, and the rest were not run. Known limits:

- The check sees only what the runner prints. A mode that prints a failed
  test's name without its error cannot show a crash, and reads it as `caught`;
  keep the runner's error reports on. With pytest 9.1, `--tb=no` and
  `--tb=line` name the error only in the summary line, after the test's name,
  cut to the terminal's width. The check runs the test with a terminal 500
  columns wide, so the error fits after any common test name: a syntax error
  there (`FAILED …::test_br001_limit -   File "…`) and any exception
  (`StopIteration`, the project's own `test_rules.LoanRefused`) give
  `crashed`, under a parametrized test's id too, spaces and brackets
  included (`test_br001_limit[a full day]`, `test_br001_limit[[8]]`). A test
  name longer than that still leaves no room, and the crash is read as
  `caught` (`unclear` under `--tb=line`).
- A parameter id that itself holds `] - ` (a closing bracket, a space, a
  dash and a space) ends the id early in pytest's summary line. Under
  `--tb=no`, a syntax error then reads as `caught`; under `--tb=line`, as
  `unclear`; an exception whose name ends neither in `Error` nor in
  `Exception` reads as `caught` under both. An exception whose name ends in
  `Error` or `Exception` still reads as `crashed`, and so does every error
  under `-q` and the default `--tb=auto`. An id holding `] - File "` reads
  every failure as `crashed`, a failed assertion too.
- The check runs the project's tests with a terminal 500 columns wide
  (`COLUMNS=500`). A test that depends on the terminal's width (one that pins
  how a help text wraps, for example) can then fail before the break, which
  gives `invalid`.
- An assertion message that holds the words "syntax error" reads as
  `crashed`, in every runner and mode: the check reads those words as a
  crash on any line of the output.
- A query that throws its own error when an element is missing makes a
  caught break read as `crashed`: the test failed because the element was
  gone, but the output shows an error, not a failed assertion. For example,
  Testing Library's `getByText` under Vitest or Jest throws
  `TestingLibraryElementError`. Write the element's test with a query that
  does not throw and an `expect` assertion (in the example,
  `expect(queryByText(…)).toBeInTheDocument()`), which reads as `caught`.
- Mocha prints a failing test's group and its title on separate lines: pass
  `--expect`.
- A runner whose output fits none of the signs gets `unclear`; `--expect`
  serves it.

**The log.** Each check appends one row to `docs/reviews/guard-checks.md`: the
element, the file, the find and replace texts kept whole, a fingerprint of the
element's text (with its Examples table for a rule), a fingerprint of the
file, the test command, the failed test and the verdict. A cell keeps every
character: `\\` is a backslash, `\|` a pipe, `\n` a line break, `\r` a
carriage return, `\t` a tab, `\s` a space at either end, and `\uXXXX` any other
control character, line separator or blank at either end. A log written by an
earlier release keeps its table; new rows go into a new table below it.

The implementer's finish check accepts a rule as guarded only from that log:
the newest row of the rule, and only when it is `caught`. It reports the row
as stale when the rule's text, its Examples table or the enforcing file
changed since it was logged, or when the row is in the earlier format, and
says to run the guard check again. A log it cannot read is the finding
`UNREADABLE`. A break you reason about but do not run counts as not done. The
verdict is information: nothing checks it for cheating, and a test weakened
while the element and its file stay the same is not detected.

The use case is found in any folder spelling the scripts accept (`use_cases`,
`use-cases`, `usecases`), the same file the finish check reads. A
specification, an enforcing file or a guard-check log the check cannot read
is the finding `UNREADABLE`: the check does not run. A log that becomes
unreadable during the run is the same finding, with the verdict in the
message and no row written. The script exits 0 whatever the verdict
or finding; with `--strict` it exits 1 unless the verdict is `caught`. It exits
1 when it cannot write the log, with the verdict in the message (the file is
restored all the same), and 2 on a usage error or when the file could not be
restored (the original is then kept beside it as `<file>.guard-backup`).

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
   | The unit's tests fail on an assertion | They guard the rule. Note which assertion failed: the failure message names it |
   | The unit's tests pass | They do not guard it. Fix the test: usually it asserts a message but not the state, or its setup never reaches the boundary |
   | Other units' tests fail too | Fine; note it. They depend on the same rule |
   | Nothing can run, or the tests stop on an error rather than an assertion | The break was too large (a syntax error, a removed function). Restore and make a smaller break |

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
