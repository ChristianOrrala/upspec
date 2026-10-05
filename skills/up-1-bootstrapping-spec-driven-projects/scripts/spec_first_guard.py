#!/usr/bin/env python3
"""Spec-first guard: flag a change set that changes behavior code without a specification behind it.

A change set passes when at least one of these holds:
  - it touches no behavior code;
  - it also changes a specification (requirements, entity model, diagram, a use
    case, a journey test case, a process model) under the docs folder;
  - a commit message or the message file carries the declaration line
        No behavior change: UC-012
    naming the use case the change stays within, or `none` with a reason.

It also flags behavior code that arrives together with a use case whose Status
is still Draft or Reviewed: nothing is implemented before approval.

Findings: CODE_WITHOUT_SPEC, DECLARATION_INCOMPLETE, NOT_APPROVED.
Output: path:line: SEVERITY CODE [element]: message
Exit code 0 when clean or in warn mode, 1 in block mode with findings, 2 on usage errors.

Usage:
    spec_first_guard.py [--base REF] [--head REF] [--docs DIR] [--code GLOB ...]
                        [--message-file FILE] [--mode warn|block]
    spec_first_guard.py --staged [--message-file FILE] [--docs DIR] [--mode warn|block]

--base defaults to HEAD~1 and --head to HEAD; the change set is what --head adds
since it left --base. --staged looks at the index instead, for a commit hook that
passes the commit message file. --code limits behavior code to paths matching the
given patterns (for example "src/*"); without it, files with a source code suffix
outside the docs folder count, tests excluded.

Requires Python 3.9+ and git, standard library only. Reads the repository; writes nothing.
"""
import argparse
import fnmatch
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model  # noqa: E402  (local module, same folder)

SOURCE_SUFFIXES = (".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".java", ".kt", ".kts", ".go", ".rb", ".php",
                   ".cs", ".rs", ".swift", ".scala", ".c", ".h", ".cc", ".cpp", ".hpp", ".sql", ".vue", ".svelte",
                   ".ex", ".exs", ".dart", ".groovy")
TEST_FOLDERS = {"test", "tests", "__tests__", "spec", "specs", "e2e", "testing", "fixtures"}
TEST_NAME = re.compile(r"(^test_.*|.*_test|.*[.-](test|spec)|.*Tests?|.*IT)\.[A-Za-z0-9]+$")
SPEC_FILES = ("requirements.md", "requirements_catalog.md", "entity_model.md", "entity-model.md", "use_cases.puml", "use-cases.puml")
SPEC_FOLDERS = ("use_cases", "use-cases", "usecases", "test_cases", "test-cases", "processes")
DECLARATION = re.compile(r"^\s*(?:[-*>]\s*)?no behaviou?r change\s*:\s*(.*)$", re.IGNORECASE)
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
NOT_YET = ("Draft", "Reviewed")


def is_test(path):
    parts = path.split("/")
    return any(p.lower() in TEST_FOLDERS for p in parts[:-1]) or bool(TEST_NAME.match(parts[-1]))


def is_spec(path, docs):
    if not path.startswith(docs + "/"):
        return False
    rest = path[len(docs) + 1:]
    return rest in SPEC_FILES or rest.split("/")[0] in SPEC_FOLDERS


def is_behavior_code(path, docs, patterns):
    if path.startswith(docs + "/") or is_test(path):
        return False
    if patterns:
        return any(fnmatch.fnmatch(path, p) for p in patterns)
    return path.endswith(SOURCE_SUFFIXES)


def declarations(text):
    """Return (complete, incomplete) declaration values found at the start of a line, outside comments."""
    complete, incomplete = [], []
    for line in COMMENT.sub("", text).splitlines():
        match = DECLARATION.match(line)
        if not match:
            continue
        value = match.group(1).strip()
        if model.RE_UC_ID.search(value) or re.match(r"none\b", value, re.IGNORECASE):
            complete.append(value)
        else:
            incomplete.append(value)
    return complete, incomplete


def main(argv):
    parser = argparse.ArgumentParser(description="Flag behavior code that changes without a specification behind it.")
    parser.add_argument("--base")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--staged", action="store_true", help="look at the index instead of a commit range")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--code", action="append", default=[], metavar="GLOB")
    parser.add_argument("--message-file", help="a commit message or pull request description to search for the declaration")
    parser.add_argument("--mode", choices=("warn", "block"), default="warn")
    args = parser.parse_args(argv)
    args.docs = args.docs or model.docs_default()
    if args.staged and args.base:
        print("--staged and --base exclude each other", file=sys.stderr)
        return 2
    code, top = model.git(["rev-parse", "--show-toplevel"])
    if code != 0:
        print("not a git repository (or git is not available)", file=sys.stderr)
        return 2
    top = top.strip()
    docs = os.path.relpath(os.path.abspath(args.docs), top).replace(os.sep, "/")

    messages = ""
    if args.staged:
        code, out = model.git(["diff", "--cached", "--name-only"], cwd=top)
    else:
        base = args.base or "HEAD~1"
        for ref in (base, args.head):
            if model.git(["rev-parse", "--verify", "--quiet", ref + "^{commit}"], cwd=top)[0] != 0:
                print("unknown revision: %s" % ref, file=sys.stderr)
                return 2
        code, out = model.git(["diff", "--name-only", "%s...%s" % (base, args.head)], cwd=top)
        messages = model.git(["log", "--format=%B", "%s..%s" % (base, args.head)], cwd=top)[1]
    if code != 0:
        print("git could not list the changed files", file=sys.stderr)
        return 2
    if args.message_file:
        try:
            with open(args.message_file, encoding="utf-8") as handle:
                messages += "\n" + handle.read()
        except (OSError, UnicodeDecodeError) as exc:
            print("cannot read %s: %s" % (args.message_file, exc), file=sys.stderr)
            return 2

    changed = [line.strip() for line in out.splitlines() if line.strip()]
    behavior = [p for p in changed if is_behavior_code(p, docs, args.code)]
    specs = [p for p in changed if is_spec(p, docs)]
    complete, incomplete = declarations(messages)

    report = model.Reporter(top)
    flag = report.error if args.mode == "block" else report.warn
    if behavior and not specs and not complete:
        shown = ", ".join(behavior[:5]) + (" and %d more" % (len(behavior) - 5) if len(behavior) > 5 else "")
        flag(os.path.join(top, behavior[0]), 0, "CODE_WITHOUT_SPEC", "-",
             "%d behavior file(s) changed (%s) with no specification change under %s/ and no line 'No behavior change: UC-XXX'"
             % (len(behavior), shown, docs))
    for value in incomplete:
        if not complete:
            flag(os.path.join(top, behavior[0] if behavior else docs), 0, "DECLARATION_INCOMPLETE", "-",
                 "'No behavior change: %s' names no use case; write the use case id, or 'none' and the reason" % value)
    if behavior:
        for path in specs:
            full = os.path.join(top, path)
            if not re.match(r"UC-\d{3}", os.path.basename(path)) or not os.path.isfile(full):
                continue
            try:
                uc = model.parse_use_case(full)
            except (OSError, UnicodeDecodeError):
                continue
            if uc.status in NOT_YET:
                flag(full, 0, "NOT_APPROVED", uc.id or "-",
                     "behavior code changes together with a use case whose Status is %s; implementation waits for Approved" % uc.status)
    report.print_text()
    print("checked: %d changed file(s), %d behavior, %d specification, declaration %s"
          % (len(changed), len(behavior), len(specs), "found" if complete else "not found"))
    return 1 if args.mode == "block" and report.findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
