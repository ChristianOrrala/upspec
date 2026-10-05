#!/usr/bin/env python3
"""List the files a change touched and whether each one belongs to the use case.

Compares the working tree (committed, staged, unstaged and untracked files)
with a base revision and sorts every changed file into one of four groups:

  specification  the use case's own file under the docs folder
  attributed     a file that carries the use case id, plain (UC-012) or compact (UC012)
  other-spec     another file under the docs folder
  unattributed   anything else: explain it, split it out, or revert it

A file-level answer is a starting point, not a verdict: read the hunks of
attributed files against the plan as well.

Exit code 0 (with --strict: 1 when a file is unattributed), 2 on usage errors.

Usage:
    scope_audit.py UC-012 [--base REF] [--docs DIR] [--strict] [--format text|json]

--base defaults to HEAD, which shows uncommitted work. On a feature branch pass
the branch it started from, for example --base main.

Requires Python 3.9+, standard library only, and git. Reads only; changes nothing.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model  # noqa: E402  (local module, same folder)


def changed_files(repo, base):
    """Return {path: status letter} for files that differ from base, including untracked ones."""
    files = {}
    code, out = model.git(["diff", "--name-status", base, "--"], cwd=repo)
    if code != 0:
        return None
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            files[parts[-1]] = parts[0][0]
    code, out = model.git(["ls-files", "--others", "--exclude-standard"], cwd=repo)
    if code == 0:
        for path in out.splitlines():
            files.setdefault(path, "A")
    return files


def carries(path, patterns):
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except (OSError, UnicodeDecodeError):
        return False
    return any(p.search(text) for p in patterns)


def main(argv):
    parser = argparse.ArgumentParser(description="Sort changed files by whether they belong to a use case.")
    parser.add_argument("use_case", help="identifier, for example UC-012")
    parser.add_argument("--base", default="HEAD")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--strict", action="store_true", help="exit 1 when a file is unattributed")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    args.docs = args.docs or model.docs_default()
    if not re.fullmatch(r"UC-\d{3}", args.use_case):
        print("use case identifier must look like UC-012", file=sys.stderr)
        return 2
    code, top = model.git(["rev-parse", "--show-toplevel"], cwd=os.getcwd())
    if code != 0:
        print("not a git repository (or git is not installed)", file=sys.stderr)
        return 2
    repo = top.strip()
    files = changed_files(repo, args.base)
    if files is None:
        print("unknown revision: %s" % args.base, file=sys.stderr)
        return 2
    docs_rel = os.path.relpath(os.path.realpath(args.docs), os.path.realpath(repo)).replace(os.sep, "/")
    plain = re.compile(r"(?<![A-Za-z0-9])%s(?!\d)" % re.escape(args.use_case))
    compact = re.compile(r"(?<![A-Za-z0-9])%s(?!\d)" % re.escape(model.compact_id(args.use_case)))
    groups = {"specification": [], "attributed": [], "other-spec": [], "unattributed": []}
    for path in sorted(files):
        status, name = files[path], os.path.basename(path)
        entry = {"path": path, "status": {"A": "added", "M": "modified", "D": "deleted", "R": "renamed"}.get(status, status)}
        if path.startswith(docs_rel + "/"):
            own = name.startswith(args.use_case + "-") or name == args.use_case + ".md"
            groups["specification" if own else "other-spec"].append(entry)
        elif plain.search(path) or compact.search(path) or (status != "D" and carries(os.path.join(repo, path), (plain, compact))):
            groups["attributed"].append(entry)
        else:
            groups["unattributed"].append(entry)
    if args.format == "json":
        print(json.dumps({"use_case": args.use_case, "base": args.base, "groups": groups}, indent=2))
    else:
        print("%s  changes since %s" % (args.use_case, args.base))
        notes = {"specification": "the use case's own file",
                 "attributed": "carries the use case id; check each hunk against the plan",
                 "other-spec": "another specification changed; is that part of this change?",
                 "unattributed": "no use case id; explain, split out, or revert"}
        for group in ("specification", "attributed", "other-spec", "unattributed"):
            print("\n%s (%d): %s" % (group, len(groups[group]), notes[group]))
            for entry in groups[group]:
                print("  %-9s %s" % (entry["status"], entry["path"]))
        if not any(groups.values()):
            print("\nno changes")
    return 1 if args.strict and groups["unattributed"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
