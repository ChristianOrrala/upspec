#!/usr/bin/env python3
"""Run one guard check: break a rule on purpose, run its test, restore, and log what happened.

A test guards a rule only if it fails when the rule is broken. This script makes
that a recorded fact instead of a claim. It:

  1. runs the test once on the code as it is (it must pass, or the check proves nothing);
  2. replaces one exact piece of one file (the break), which must occur exactly once;
  3. runs the test again;
  4. always puts the file back and checks it is byte for byte what it was;
  5. appends one row to the guard-check log (DIR/reviews/guard-checks.md).

Verdicts: caught (passed before, failed after the break), not caught (passed
both times: the test does not guard the rule), invalid (the test failed before
the break). The implementer's finish check reads the log: every rule in a
change needs a break that a test caught.

The test command is run exactly as given, through the shell, from the current
folder. The file must lie inside the current folder.

Usage:
    guard_check.py "UC-012 BR-001" --file PATH --find TEXT --replace TEXT --test COMMAND
                   [--docs DIR] [--timeout SECONDS] [--format text|json]

Exit code 0 caught, 1 not caught or invalid, 2 on usage errors or when the file
could not be restored (then the original is kept beside it as PATH.guard-backup).

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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model  # noqa: E402  (local module, same folder)

UNIT = re.compile(r"^UC-\d{3} (?:BR-\d{3}|A\d+)$")
# A unit's tests run in seconds to a few minutes; ten minutes means the command hangs.
DEFAULT_TIMEOUT = 600
# Long enough to read the break in the log, short enough to keep one row per line.
CELL_CHARS = 80
HEADER = ("# Guard checks\n\nOne row per deliberate break, written by guard_check.py. The newest row "
          "for a unit is its current result.\n\n| When (UTC) | Unit | File | Break | Test | Verdict |\n"
          "|---|---|---|---|---|---|\n")


def cell(text):
    text = " ".join(str(text).split()).replace("|", "/")
    return text if len(text) <= CELL_CHARS else text[:CELL_CHARS - 1] + "…"


def run(command, timeout):
    """Exit code of the command, or None when it ran past the timeout."""
    # No bytecode cache: a break of the same size written in the same second would
    # otherwise be read from a cache compiled before it.
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        return subprocess.run(command, shell=True, timeout=timeout, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
    except subprocess.TimeoutExpired:
        return None


def write(path, data, offset):
    """Write the file and move its time forward, so that any build cache sees a change."""
    with open(path, "wb") as handle:
        handle.write(data)
    stamp = time.time() + offset
    os.utime(path, (stamp, stamp))


def break_and_test(target, original, broken, command, timeout):
    """Run the test against the broken file; always restore. Returns (exit code or None, restored)."""
    digest = hashlib.sha256(original).hexdigest()
    try:
        write(target, broken, 1)
        return run(command, timeout), None
    finally:
        write(target, original, 2)
        with open(target, "rb") as handle:
            restored = hashlib.sha256(handle.read()).hexdigest() == digest
        if not restored:
            with open(target + ".guard-backup", "wb") as handle:
                handle.write(original)
        RESTORED[target] = restored


RESTORED = {}


def log_row(docs, row):
    folder = os.path.join(docs, "reviews")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "guard-checks.md")
    new = not os.path.isfile(path)
    with open(path, "a", encoding="utf-8") as handle:
        if new:
            handle.write(HEADER)
        handle.write("| %s |\n" % " | ".join(cell(v) for v in row))
    return path


def main(argv):
    parser = argparse.ArgumentParser(description="Break a rule on purpose, run its test, restore, log.")
    parser.add_argument("unit", help='the rule or flow, for example "UC-012 BR-001"')
    parser.add_argument("--file", required=True, help="the file that enforces it")
    parser.add_argument("--find", required=True, help="the exact text to replace; it must occur once")
    parser.add_argument("--replace", required=True, help="the text that breaks the rule")
    parser.add_argument("--test", required=True, help="the command that runs the unit's tests")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    args.docs = args.docs or model.docs_default()
    stop = model.stop_if_old(model.Docs(args.docs))
    if stop is not None:
        return stop

    if not UNIT.match(args.unit):
        print('unit must look like "UC-012 BR-001" or "UC-012 A1"', file=sys.stderr)
        return 2
    here = os.path.realpath(os.getcwd())
    target = os.path.realpath(args.file)
    if not target.startswith(here + os.sep) or not os.path.isfile(target):
        print("no such file inside the current folder: %s" % args.file, file=sys.stderr)
        return 2
    if args.find == args.replace:
        print("--replace must differ from --find", file=sys.stderr)
        return 2
    with open(target, "rb") as handle:
        original = handle.read()
    text = original.decode("utf-8")
    count = text.count(args.find)
    if count != 1:
        print("the text to replace occurs %d times in %s; give a longer piece so it occurs once" % (count, args.file), file=sys.stderr)
        return 2
    before = run(args.test, args.timeout)
    after = None
    if before == 0:
        after, _ = break_and_test(target, original, text.replace(args.find, args.replace, 1).encode("utf-8"), args.test, args.timeout)
        if not RESTORED.get(target):
            print("could not restore %s; the original is in %s.guard-backup" % (args.file, args.file), file=sys.stderr)
            return 2

    if before != 0:
        verdict = "invalid: the test does not pass before the break" if before is not None else "invalid: the test ran past the timeout"
    elif after is None:
        verdict = "invalid: the test ran past the timeout after the break"
    else:
        verdict = "caught" if after != 0 else "not caught"
    when = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
    rel = os.path.relpath(target, here)
    path = log_row(args.docs, [when, args.unit, rel, "%s -> %s" % (args.find, args.replace), args.test, verdict])
    result = {"unit": args.unit, "file": rel, "verdict": verdict, "log": os.path.relpath(path, here), "restored": True}
    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print("%s: %s (break in %s; file restored; logged in %s)" % (args.unit, verdict, rel, result["log"]))
    return 0 if verdict == "caught" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
