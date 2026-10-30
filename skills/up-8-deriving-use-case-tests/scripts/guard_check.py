#!/usr/bin/env python3
"""Run one guard check: break a rule on purpose, run its test, restore, and log what happened.

A test guards a rule only if it fails when the rule is broken. This script makes
that a recorded fact instead of a claim. It:

  1. runs the test once on the code as it is (it must pass, or the check proves nothing);
  2. replaces one exact piece of one file (the break), which must occur exactly once;
  3. runs the test again;
  4. always puts the file back and checks it is byte for byte what it was;
  5. appends one row to the guard-check log (DIR/reviews/guard-checks.md): the
     element, the file, the find and replace texts, a fingerprint of the
     element's text (with its Examples table for a rule) and one of the file,
     the test command, the failed test and the verdict. Each text is kept
     whole, line breaks and pipes included. A log of an earlier release keeps
     its table; a new table goes below it.

The test's output (standard output and error together, kept in memory) is
read for the verdict of the break:

  caught      a test whose name holds both the use case and the element failed
              on an assertion (UC-012 with BR-005, A2, step 3, pre1 or
              post-s-1, in common spellings: test_uc012_br005,
              UC012Test.test_br005, testUc012Br005, a displayed name such as
              "UC-012 BR-005 rejects ..."), or the text given with --expect
              appeared, for a runner that prints no names;
  crashed     the output shows an error rather than a failed assertion: a syntax
              error, a failed import, an exception the test did not expect, a
              build that did not compile;
  not caught  the test still passed: it does not guard the element;
  unclear     the test failed, but the output does not say that the element's
              test failed (another use case's BR-001 does not count).

The element's own report decides first: what the output shows from the line
that reports the element's test to the next test's report. It is crashed when
that part shows an error or the runner marks the test as an error. Otherwise
it is caught, unless the output shows an error outside every test's report
(before the first report, or in a section of the whole run): then it is
unclear, because the output does not say whether that error was the element's
test. Another test's error does not change it. The --expect text is read the
same way, except that an error outside every report does not make it unclear:
the developer named the evidence. Only when the output names neither does an
error anywhere in it make the verdict crashed.

An explanation of a failed assertion is not an error: an exception's name
without an Error or Exception ending counts only on the line right after a
traceback's frame and its source lines, and a bare "Error:" whose label is
padded to a column is a field of an assertion's report (Go's testify prints
"Error:      <tab>Not equal:"). The signs follow the documented output of the
runners named in the comments below as examples; the tests run unittest,
pytest and stand-in runners that print the other shapes.

A test that fails before the break is invalid: the check proves nothing. The
verdict is information for the developer; nothing checks it. The implementer's
finish check reads the log and counts only caught.

The test command is run exactly as given, through the shell, from the current
folder. The file must lie inside the current folder.

The element is any element of the use case, in the finish check's names:
"UC-012 BR-005", "UC-012 A2", "UC-012 Step 3", "UC-012 Pre-1", "UC-012 Post-S-1",
"UC-012 Post-F-2". It must exist in the use case's specification.

Usage:
    guard_check.py "UC-012 BR-001" --file PATH --find TEXT --replace TEXT --test COMMAND
                   [--expect TEXT] [--docs DIR] [--timeout SECONDS] [--format text|json] [--strict]

For crashed and unclear, the report also shows the lines of the output that are
new since the run before the break (the first OUTPUT_LINES of them, and how many
there were), so that the developer can read what happened.

Exit code 0 when the check ran, whatever the verdict (with --strict 1 unless it
is caught). A file it needs and cannot read (the specification, the enforcing
file, the guard-check log) is the finding UNREADABLE: the check does not run,
and exits 0, or 1 with --strict. A log that could be read before the break and
cannot be read when the row is written is the same finding, with the verdict in
the message and no row written. Exit 1 also when the log cannot be written,
with the verdict in the message; 2 on usage errors or when the file could not
be restored (then the original is kept beside it as PATH.guard-backup).

Requires Python 3.9+, standard library only.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from typing import NamedTuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model  # noqa: E402  (local module, same folder)

# A unit's tests run in seconds to a few minutes; ten minutes means the command hangs.
DEFAULT_TIMEOUT = 600
# The terminal width a runner sees. A runner that fits its lines to the terminal (pytest cuts its summary line to 80
# columns when the output is piped) cuts a failed test's error away after a long test name; five hundred columns hold
# a deep path's test id, the exception's name and the start of its message.
OUTPUT_COLUMNS = "500"


def run(command, timeout):
    """(exit code or None when it ran past the timeout, standard output and error together)."""
    # No bytecode cache: a break of the same size written in the same second would
    # otherwise be read from a cache compiled before it.
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", COLUMNS=OUTPUT_COLUMNS)
    try:
        done = subprocess.run(command, shell=True, timeout=timeout, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)
        return done.returncode, done.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired as exc:
        return None, (exc.output or b"").decode("utf-8", "replace")


# --- reading the output: stack-neutral signs, each runner named only as an example ---
# These signs follow the documented output of each runner named below; the tests run unittest, pytest and stand-in
# runners that print the other shapes. A runner whose output fits none of them gets unclear, and --expect serves it.

# A line that reports one test's result: unittest "FAIL: name" and "ERROR: name" (and "name ... FAIL" when verbose),
# pytest "FAILED path::name", Go "--- FAIL: name", .NET "Failed name", Jest and Vitest "✕ name" and "● name", other
# runners' "×", "✗", "✘", TAP "not ok", a numbered entry of a failure list (Mocha, RSpec, PHPUnit "1) name"), JUnit
# "name  Time elapsed ... <<< FAILURE!", Gradle "Class > name FAILED", a Maven summary entry "[ERROR]   Class.name:12".
REPORT_LINE = re.compile(r"^\s*(?:FAIL\b|FAILED\b|ERROR\b|Failed\b|---\s+FAIL\b|not ok\b|\d+\)\s"
                         r"|[\u2715\u00d7\u2717\u2718\u25cf])|<<<\s*(?:FAILURE|ERROR)!|\.\.\.\s+(?:FAIL|ERROR)\s*$"
                         r"|\sFAILED\s*$|^\[ERROR\]\s+\S+[.#]\w+:\d+")
# A rule with a title, as pytest heads each failure's section ("____ name ____") and its summary ("=== ... ===").
TITLED_RULE = re.compile(r"^\s*([=_\-~*#])\1{2,}\s+(\S.*?)\s+\1{3,}\s*$")
# A titled rule whose title is words only heads a section of the whole run, not one test ("=== FAILURES ===", "===
# short test summary info ==="): an error under it, with no test's report between, is not attributed to any test.
SECTION_TITLE = re.compile(r"[A-Za-z][A-Za-z ]*")
# The runner's own sign that a test raised an error instead of failing an assertion: unittest "ERROR: name" and
# "... ERROR", pytest "ERROR path::name", JUnit "<<< ERROR!".
RUNNER_ERROR = re.compile(r"^\s*ERROR\b|\.\.\.\s+ERROR\s*$|<<<\s*ERROR!")
# An error named at the start of a line, or after a summary's " - " (pytest) or " » " (Maven): Python's
# "SyntaxError: ...", pytest's "E   ModuleNotFoundError: ...", JavaScript's "TypeError: ..." and a plain "Error: ...",
# Java's "java.lang.NullPointerException" (Gradle adds " at File.java:15"), .NET's "System.NullReferenceException : ...",
# Ruby's "NoMethodError:".
NAMED_ERROR = re.compile(r"(?:^\s*(?:E\s+|>\s*|\[ERROR\]\s*|Caused by:\s*|Uncaught\s+)?|\s[-\u00bb]\s)"
                         r"((?:[A-Za-z_][\w$]*(?:\.|::))*(?:[A-Z][\w$]*)?(?:Error|Exception))(?=\s?:|\s+at\b|\s*\[|\s*$)")
# A bare Error or Exception whose label is padded to a column is a field of an assertion's report, not an exception:
# Go's testify prints a failed assertion as "Error Trace:\t...", "Error:      \tNot equal:", "Test:       \t...". An
# exception's message follows its colon after one space ("Error: not configured").
REPORT_FIELD = re.compile(r"\s*:(?:[ ]*\t|[ ]{2,})")
# A traceback's frame, the place an exception passed through: Python's "File "...", line 12" (and the "Traceback
# (most recent call last):" above it), pytest's "path.py:12: in name" (--tb=short) and its ">" source line.
TRACEBACK_FRAME = re.compile(r'^\s*(?:Traceback \(most recent call last\):|File ".*", line \d+)|^\S.*:\d+: in \S|^>')
# An exception whose name has neither ending, as Python prints it: the first line that is not indented after a
# traceback's frame and its source lines ("LoanRefused: no loan", "StopIteration"), or the first pytest "E   " line
# after one. A later "E" line, or such a line without a frame before it, explains an assertion (pytest's diff line
# "E           Loan", xUnit's "Expected: 8").
TRACEBACK_EXCEPTION = re.compile(r"^(E\s+)?((?:[A-Za-z_]\w*\.)*[A-Z]\w*[a-z]\w*)(?::\s.*)?\s*$")
# A test's id in a summary line: pytest's "path::Class::name", and a parametrized test's id in brackets, which may
# hold spaces and brackets of its own ("test_uc001_br001_limit[a full day]", "[[8]]", "[a]b]", "[a [x] day]"). The id
# ends at the first "]" that " - " follows, where the message starts; a "]" before it belongs to the id. A parameter
# id that itself holds "] - " is not read whole.
SUMMARY_ID = r"[^\s\[]+(?:\[(?:[^\]]|\](?!\s+-\s))*\])?"
# A summary line that names an exception after the test id, as pytest's short summary does
# ("FAILED path::name - StopIteration", "FAILED path::name - test_rules.LoanRefused: no loan"): the name may have
# neither ending, since the summary is the only place --tb=no and --tb=line name it.
SUMMARY_EXCEPTION = re.compile(r"^(?:FAILED|ERROR)\s+" + SUMMARY_ID
                               + r"\s+-\s+((?:[A-Za-z_]\w*\.)*[A-Z]\w*[a-z]\w*)(?::\s.*)?\s*$")
# Errors that name an assertion are failed assertions, not crashes: Python's and JavaScript's AssertionError, JUnit's
# AssertionFailedError, PHPUnit's ExpectationFailedException, xUnit's assertion exceptions, pytest's Failed (DID NOT
# RAISE).
ASSERTION_ERROR = re.compile(r"Assert|Expectation|^Xunit\.Sdk\.|(?:^|\.)Failed$")
# Errors with no exception name: Go "panic:" and "[build failed]", a syntax error in Go, Ruby or a shell, Maven
# "COMPILATION ERROR", javac "cannot find symbol", TypeScript "error TS2304", Rust "error[E0425]", Node "Cannot find
# module", Jest "Test suite failed to run", pytest "while importing test module", PHP "Parse error:". A failure summary
# whose message is a place in a file, not an exception's name, is a syntax error: pytest's short summary gives a
# SyntaxError's message as "FAILED path::name -   File "...", line 1", where a failed assertion's names the assertion.
# Only the place right after the summary's test id counts: pytest's diff of two messages that hold such a place
# ("E     - File "orders.csv" ...") and an assertion's message in the summary line itself explain a failed assertion.
CRASH_SIGN = re.compile(r"\bpanic:|\[build failed\]|(?i:\bsyntax error\b)|COMPILATION ERROR|Compilation failure"
                        r'|^(?:FAILED|ERROR)\s+' + SUMMARY_ID + r'\s+-\s+File "'
                        r"|cannot find symbol|\berror TS\d+|\berror\[E\d+\]|Cannot find module|Test suite failed to run"
                        r"|while importing test module|\b(?:Parse|Fatal) error:|Segmentation fault")
# Durations differ between two runs of the same passing test ("(3 ms)", "0.01s"); they never tell lines apart.
DURATION = re.compile(r"\d+(?:\.\d+)?\s*(?:ms|s|sec|seconds)\b")
# Forty lines fit one screen: enough to see what the run printed after the break, few enough to keep the report short.
OUTPUT_LINES = 40


class Judgement(NamedTuple):
    """The verdict of a run that failed after the break, the line that shows it, the failed test's line (empty
    unless caught), and the run's lines that are new since the run before the break."""
    verdict: str
    evidence: str
    failed_test: str
    output: list


def crash_in(line, after_frame):
    """The line shows an error rather than a failed assertion; after_frame says that it is the first line after a
    traceback's frame and its indented source lines, where an exception's own line stands."""
    named = NAMED_ERROR.search(line)
    if (named and not ASSERTION_ERROR.search(named.group(1))
            and not (named.group(1) in ("Error", "Exception") and REPORT_FIELD.match(line, named.end(1)))):
        return True
    raised = TRACEBACK_EXCEPTION.match(line)
    if raised and after_frame and not ASSERTION_ERROR.search(raised.group(2)):
        return True
    summary = SUMMARY_EXCEPTION.match(line)
    if summary and not ASSERTION_ERROR.search(summary.group(1)):
        return True
    return bool(CRASH_SIGN.search(line))


def judge(after, before, element, expect=None):
    """The Judgement of a test run that failed after the break.

    Only lines new since the run before the break count, so that what a passing run prints anyway (a test's name, a
    logged error) never decides. The element's own report decides first: from a report line (or a titled rule) that
    names the element to the next report line or titled rule about another test. That block is crashed when it shows
    an error (or the runner marks the test as an error). Otherwise it is caught, or unclear when an error stands
    outside every test's report (before the first report, or in a section of the whole run). The --expect text's
    block is read the same way, but an error outside every report leaves it caught. Only when neither is there does
    an error anywhere make the run crashed."""
    seen = {DURATION.sub("", line).strip() for line in before.splitlines()}
    lines, crashes, in_frame = [], [], False
    for line in after.splitlines():
        if not line.strip():
            continue
        # A frame opens; its indented source lines keep it open; the next line is read as the exception's own.
        frame = bool(TRACEBACK_FRAME.match(line))
        after_frame = in_frame and not frame and not line[:1].isspace()
        if DURATION.sub("", line).strip() not in seen:
            lines.append(line)
            crashes.append(crash_in(line, after_frame))
        in_frame = frame or (in_frame and line[:1].isspace())
    output = [line.rstrip() for line in lines]

    def heads(line):
        return bool(REPORT_LINE.search(line) or TITLED_RULE.search(line))

    def blocks(starts):
        """[(start index, end index)] of the blocks whose first line satisfies starts."""
        found, open_at = [], None
        for index, line in enumerate(lines):
            if starts(line):
                if open_at is not None:
                    found.append((open_at, index))
                open_at = index
            elif open_at is not None and heads(line):
                found.append((open_at, index))
                open_at = None
        if open_at is not None:
            found.append((open_at, len(lines)))
        return found

    def section(line):
        titled = TITLED_RULE.search(line)
        return bool(titled and SECTION_TITLE.fullmatch(titled.group(2)))

    def unattributed():
        """An error printed outside every test's report: before the first report, or in a section of the whole
        run (a mode that prints errors apart from the tests, such as pytest --tb=line)."""
        spans = [(0, next((i for i, line in enumerate(lines) if heads(line)), len(lines)))]
        spans += [(begin + 1, end) for begin, end in blocks(section)]
        return next((lines[i].strip() for begin, end in spans for i in range(begin, end) if crashes[i]), None)

    def read(spans, failed, named):
        for begin, end in spans:
            # The error itself is the better evidence; the runner's mark on the test is shown when it names none.
            crash = next((lines[i].strip() for i in range(begin, end) if crashes[i]), None)
            if crash or RUNNER_ERROR.search(lines[begin]):
                return Judgement("crashed", crash or lines[begin].strip(), "", output)
        stray = unattributed() if named else None
        if stray:
            return Judgement("unclear", "the element's test failed, but the output shows an error outside every "
                             "test's report, so it does not say whether that test crashed: %s" % stray, "", output)
        return Judgement("caught", failed, failed, output)

    own = blocks(lambda line: heads(line) and element.named_in(line))
    reports = [lines[begin].strip() for begin, _ in own if REPORT_LINE.search(lines[begin])]
    if reports:
        return read(own, reports[0], True)
    if expect and after.count(expect) > before.count(expect):
        # The developer named the text that shows the element's failure; the runner names no tests to attribute by.
        return read(blocks(lambda line: expect in line), expect, False)
    crash = next((line.strip() for line, crashed in zip(lines, crashes) if crashed), None)
    if crash:
        return Judgement("crashed", crash, "", output)
    reason = ("the expected text did not appear: %s" % expect if expect else
              "the output names no failed test of %s" % str(element))
    return Judgement("unclear", reason, "", output)


def write(path, data, offset):
    """Write the file and move its time forward, so that any build cache sees a change."""
    with open(path, "wb") as handle:
        handle.write(data)
    stamp = time.time() + offset
    os.utime(path, (stamp, stamp))


def break_and_test(target, original, broken, command, timeout):
    """Run the test against the broken file and always restore it. Returns (exit code or None, output, restored);
    when the file could not be restored, the original is kept beside it as PATH.guard-backup."""
    digest = hashlib.sha256(original).hexdigest()
    try:
        write(target, broken, 1)
        code, output = run(command, timeout)
    finally:
        write(target, original, 2)
        with open(target, "rb") as handle:
            restored = hashlib.sha256(handle.read()).hexdigest() == digest
        if not restored:
            with open(target + ".guard-backup", "wb") as handle:
                handle.write(original)
    return code, output, restored


def unreadable(path, exc, strict):
    """The finding UNREADABLE for a file the check needs and cannot read: reported like any finding of a check,
    exit 0, or 1 with --strict. The check does not run without it."""
    print("%s:0: ERROR UNREADABLE: cannot read: %s; the guard check did not run" % (path, exc), file=sys.stderr)
    return 1 if strict else 0


def main(argv):
    parser = argparse.ArgumentParser(description="Break an element on purpose, run its test, restore, log.")
    parser.add_argument("element", help='the element, for example "UC-012 BR-001", "UC-012 A2" or "UC-012 Step 3"')
    parser.add_argument("--file", required=True, help="the file that enforces it")
    parser.add_argument("--find", required=True, help="the exact text to replace; it must occur once")
    parser.add_argument("--replace", required=True, help="the text that breaks the element")
    parser.add_argument("--test", required=True, help="the command that runs the element's tests")
    parser.add_argument("--expect", help="text that shows the element's test failed, for a runner that prints no test names")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--strict", action="store_true", help="exit 1 unless the break was caught (default: exit 0, the verdict is reported)")
    args = parser.parse_args(argv)
    args.docs = args.docs or model.docs_default()
    docs = model.Docs(args.docs)
    stop = model.stop_if_old(docs, strict=args.strict)
    if stop is not None:
        return stop

    element = model.Element.parse(args.element)
    if element is None:
        print('the element must look like "UC-012 BR-001", "UC-012 A1", "UC-012 Step 3", "UC-012 Pre-1" or '
              '"UC-012 Post-S-1"', file=sys.stderr)
        return 2
    spec = model.find_use_case(docs, element.use_case)
    if spec is None:
        print("no specification for %s under %s" % (element.use_case, args.docs), file=sys.stderr)
        return 2
    try:
        uc = model.parse_use_case(spec)
    except (OSError, UnicodeDecodeError) as exc:
        return unreadable(spec, exc, args.strict)
    element_text = element.text(uc)
    if element_text is None:
        print("%s has no %s in %s" % (element.use_case, element.name, os.path.relpath(spec)), file=sys.stderr)
        return 2
    here = os.path.realpath(os.getcwd())
    target = os.path.realpath(args.file)
    if not target.startswith(here + os.sep) or not os.path.isfile(target):
        print("no such file inside the current folder: %s" % args.file, file=sys.stderr)
        return 2
    if args.find == args.replace:
        print("--replace must differ from --find", file=sys.stderr)
        return 2
    try:
        with open(target, "rb") as handle:
            original = handle.read()
        text = original.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return unreadable(args.file, exc, args.strict)
    log = os.path.join(args.docs, model.GUARD_LOG_NAME)
    try:
        model.read_guard_log(log)
    except (OSError, UnicodeDecodeError) as exc:
        return unreadable(log, exc, args.strict)
    count = text.count(args.find)
    if count != 1:
        print("the text to replace occurs %d times in %s; give a longer piece so it occurs once" % (count, args.file), file=sys.stderr)
        return 2
    before, before_output = run(args.test, args.timeout)
    after = after_output = None
    if before == 0:
        after, after_output, restored = break_and_test(target, original, text.replace(args.find, args.replace, 1).encode("utf-8"),
                                                       args.test, args.timeout)
        if not restored:
            print("could not restore %s; the original is in %s.guard-backup" % (args.file, args.file), file=sys.stderr)
            return 2

    judgement = Judgement("", "", "", [])
    if before != 0:
        verdict = "invalid: the test does not pass before the break" if before is not None else "invalid: the test ran past the timeout"
    elif after is None:
        verdict = "invalid: the test ran past the timeout after the break"
    elif after == 0:
        verdict = "not caught"
    else:
        judgement = judge(after_output, before_output, element, args.expect)
        verdict = judgement.verdict
    when = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
    # The file is named from the project's root, where the finish check looks for it again.
    rel = os.path.relpath(target, os.path.realpath(model.project_root(args.docs))).replace(os.sep, "/")
    row = model.GuardRow(when=when, element=str(element), file=rel, find=args.find, replace=args.replace,
                         element_fingerprint=model.fingerprint(element_text), file_fingerprint=model.fingerprint(original),
                         test=args.test, failed_test=judgement.failed_test, verdict=verdict)
    try:
        path = model.append_guard_row(args.docs, row)
    except UnicodeDecodeError as exc:
        # Read before the break and spoiled since: the same finding, with what the run found.
        print("%s:0: ERROR UNREADABLE: cannot read: %s; the verdict was %s, %s is restored, and no row was written"
              % (log, exc, verdict, args.file), file=sys.stderr)
        return 1 if args.strict else 0
    except OSError as exc:
        print("cannot write the guard-check log under %s: %s; the verdict was %s, and %s is restored"
              % (args.docs, exc, verdict, args.file), file=sys.stderr)
        return 1
    # The new output is shown when the verdict asks the developer to read it.
    shown = judgement.output[:OUTPUT_LINES] if verdict in ("crashed", "unclear") else []
    result = {"unit": str(element), "element": str(element), "file": rel, "verdict": verdict,
              "evidence": judgement.evidence, "failed_test": judgement.failed_test,
              "output": shown, "output_lines": len(judgement.output) if shown else 0,
              "log": os.path.relpath(path, here), "restored": True}
    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("%s: %s%s (break in %s; file restored; logged in %s)"
              % (element, verdict, " (%s)" % judgement.evidence if judgement.evidence else "", rel, result["log"]))
        if shown:
            total = len(judgement.output)
            print("Output new since the run before the break (%s):"
                  % ("first %d of %d new lines" % (len(shown), total) if total > len(shown) else "%d new lines" % total))
            print("\n".join("  " + line for line in shown))
    # The verdict is the output; only a strict run turns it into a failure.
    return 1 if args.strict and verdict != "caught" else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
