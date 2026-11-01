#!/usr/bin/env python3
"""Spec-first guard: flag a change set that changes behavior code without a specification behind it.

A change set passes when at least one of these holds:
  - it touches no behavior code;
  - it also changes a specification (requirements, entity model, diagram, a use
    case, a journey test case, a process model) under the docs folder;
  - a commit message or the message file carries the declaration line
        No behavior change: UC-012
    naming the use case the change stays within, or `none` with a reason;
  - a commit message or the message file carries the light path's note
        Fixes: UC-012 BR-005
    for a bug fixed against a clear specification. The note is read, never
    checked: the guard does not ask whether the element exists or a test
    fails.

It also flags behavior code that arrives together with a use case whose Status
is still Draft or Reviewed: nothing is implemented before approval.

Findings: CODE_WITHOUT_SPEC, DECLARATION_INCOMPLETE, NOT_APPROVED, always as
warnings: the guard informs and never stops the work.
Output: path:line: SEVERITY CODE [element]: message
Exit code 0 when it ran, whatever it found (with --strict 1 on a finding), 2 on
usage errors. --mode block is still accepted and behaves as warn, with one line
saying that --strict is the explicit choice for a strict pipeline.

Usage:
    spec_first_guard.py [--base REF] [--head REF] [--docs DIR] [--code GLOB ...]
                        [--message-file FILE] [--strict]
    spec_first_guard.py --staged [--message-file FILE] [--docs DIR] [--strict]

--base defaults to HEAD~1 and --head to HEAD; the change set is what --head adds
since it left --base. An empty tree is also accepted as --base to judge a
root commit from nothing. --staged looks at the index instead, for a commit hook that
passes the commit message file. --code limits behavior code to paths matching the
given patterns (for example "src/*"); without it, files with a source code suffix
outside the docs folder count, tests excluded.

Requires Python 3.9+ and git, standard library only. Reads the repository; writes nothing.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model  # noqa: E402  (local module, same folder)

# the release these copies belong to; hook_gate.py refuses siblings of another release
UPSPEC_VERSION = "1.4.0"

NOT_YET = ("Draft", "Reviewed")


def main(argv):
    parser = argparse.ArgumentParser(description="Flag behavior code that changes without a specification behind it.")
    parser.add_argument("--base")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--staged", action="store_true", help="look at the index instead of a commit range")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--code", action="append", default=[], metavar="GLOB")
    parser.add_argument("--message-file", help="a commit message or pull request description to search for the declaration")
    parser.add_argument("--mode", choices=("warn", "block"), default="warn",
                        help="accepted for older pipelines; both modes warn")
    parser.add_argument("--strict", action="store_true", help="exit 1 on a finding (default: exit 0, findings are reported)")
    args = parser.parse_args(argv)
    args.docs = args.docs or model.docs_default()
    docs_model = model.Docs(args.docs)
    stop = model.stop_if_old(docs_model, strict=args.strict)
    if stop is not None:
        return stop
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
        # A first push has no parent; only an empty tree may stand in for its missing commit base.
        kind_code, kind = model.git(["cat-file", "-t", base], cwd=top)
        tree_code, entries = (model.git(["ls-tree", base], cwd=top)
                              if kind_code == 0 and kind.strip() == "tree" else (1, ""))
        empty_base = tree_code == 0 and not entries.strip()
        for ref in ((args.head,) if empty_base else (base, args.head)):
            if model.git(["rev-parse", "--verify", "--quiet", ref + "^{commit}"], cwd=top)[0] != 0:
                print("unknown revision: %s" % ref, file=sys.stderr)
                return 2
        if empty_base:
            code, out = model.git(["diff", "--name-only", base, args.head], cwd=top)
            messages = model.git(["log", "--format=%B", args.head], cwd=top)[1]
        else:
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
    # The same reading as the hook gate's end-of-turn question (spec_model.read_change).
    reading = model.read_change(changed, docs, lambda path: docs_model.kind(os.path.join(top, path)), messages, args.code)
    behavior, specs, complete = reading.behavior, reading.specs, reading.complete

    report = model.Reporter(top)
    if reading.code_without_spec():
        report.warn(os.path.join(top, behavior[0]), 0, "CODE_WITHOUT_SPEC", "-", reading.summary(docs))
    for value in reading.incomplete:
        if not complete:
            report.warn(os.path.join(top, behavior[0] if behavior else docs), 0, "DECLARATION_INCOMPLETE", "-",
                 "'No behavior change: %s' names no use case; write the use case id, or 'none' and the reason" % value)
    if behavior:
        for path in specs:
            full = os.path.join(top, path)
            if docs_model.kind(full) != "use_case" or not os.path.isfile(full):
                continue
            try:
                uc = model.parse_use_case(full)
            except (OSError, UnicodeDecodeError):
                continue
            if uc.status in NOT_YET:
                report.warn(full, 0, "NOT_APPROVED", uc.id or "-",
                     "behavior code changes together with a use case whose Status is %s; implementation waits for Approved" % uc.status)
    report.print_text()
    print("checked: %d changed file(s), %d behavior, %d specification, declaration %s, Fixes note %s"
          % (len(changed), len(behavior), len(specs), "found" if complete else "not found",
             "found" if reading.fixes else "not found"))
    if args.mode == "block":
        print("--mode block now warns like --mode warn; pass --strict to make findings fail a strict pipeline")
    # The findings are the output; only a strict run turns them into a failure.
    return 1 if args.strict and report.findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
