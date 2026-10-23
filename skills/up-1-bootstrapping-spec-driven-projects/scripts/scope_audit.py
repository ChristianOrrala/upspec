#!/usr/bin/env python3
"""List the files a change touched and whether each one belongs to the use case.

Compares the working tree (committed, staged, unstaged and untracked files)
with a base revision and sorts every changed file into one of five groups:

  specification  the use case's own file under the docs folder
  attributed     a path or text carrying the id, or a deletion named in the record
  tracking       an A-file at the repository root
  other-spec     another file under the docs folder
  unattributed   changed, not part of this change (a warning to the finish check)

A file-level answer is a starting point, not a verdict: read the hunks of
attributed files against the plan as well.

Exit code 0 (with --strict: 1 when a file is unattributed), 2 on usage errors.

Usage:
    scope_audit.py UC-012 [--base REF] [--record PATH] [--docs DIR] [--strict] [--format text|json]

--base defaults to HEAD, which shows uncommitted work. On a feature branch pass
the branch it started from, for example --base main.

Requires Python 3.9+, standard library only, and git. Reads only; changes nothing.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model  # noqa: E402  (local module, same folder)
import change_view  # noqa: E402

# the release these copies belong to; hook_gate.py refuses siblings of another release
UPSPEC_VERSION = "1.2.0"


def attribute(view: change_view.ChangeView, uc_ids: set[str], record: str | None = None) -> dict[str, list[dict]]:
    """Group changed paths using the shared scope policy; record is a file path."""
    groups = {"specification": [], "attributed": [], "tracking": [], "other-spec": [], "unattributed": []}
    patterns = [pattern for uc_id in sorted(uc_ids) for pattern in model._marker_patterns(uc_id)]
    deleted = {os.path.relpath(path, view.root).replace(os.sep, "/")
               for path in view.deleted_carrying(uc_ids)}
    text = (view.text(record) if record else None) or ""
    named = {path.strip() for path in re.findall(r"`([^`]+)`", text)}
    targets = model.RE_LINK.findall(text)
    targets += re.findall(r'\[[^\]\n]*\]\(<([^>\n]+)>(?:\s+"[^"]*")?\)', text)
    named.update(unquote(path) for path in targets)
    for path, status in sorted(view.changed.items()):
        entry = {"path": path, "status": {"A": "added", "M": "modified", "D": "deleted", "R": "renamed"}.get(status, status)}
        name = os.path.basename(path)
        kind = view.kind(path)
        if kind is not None:
            identifier = model.RE_UC_ID.match(name)
            own = kind == "use_case" and identifier is not None and identifier.group() in uc_ids
            group = "specification" if own else "other-spec"
        elif path in change_view.A_FILES:
            group = "tracking"
        elif model.ids_named_by_path(path) & uc_ids:
            group = "attributed"
        elif status != "D" and any(pattern.search(view.text(path) or "") for pattern in patterns):
            group = "attributed"
        elif status == "D" and (path in deleted or path in named):
            group = "attributed"
        else:
            group = "unattributed"
        groups[group].append(entry)
    return groups


def main(argv):
    parser = argparse.ArgumentParser(description="Sort changed files by whether they belong to a use case.")
    parser.add_argument("use_case", help="identifier, for example UC-012")
    parser.add_argument("--base", default="HEAD")
    parser.add_argument("--record", help="change record (default: find the newest record for this use case)")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--strict", action="store_true", help="exit 1 when a file is unattributed")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    args.docs = args.docs or model.docs_default()
    stop = model.stop_if_old(model.Docs(args.docs))
    if stop is not None:
        return stop
    if not re.fullmatch(r"UC-\d{3}", args.use_case):
        print("use case identifier must look like UC-012", file=sys.stderr)
        return 2
    code, top = model.git(["rev-parse", "--show-toplevel"], cwd=os.getcwd())
    if code != 0:
        print("not a git repository (or git is not installed)", file=sys.stderr)
        return 2
    repo = top.strip()
    docs_rel = os.path.relpath(os.path.realpath(args.docs), os.path.realpath(repo)).replace(os.sep, "/")
    try:
        view = change_view.view_for(repo, args.base, docs_rel)
    except change_view.BaseError as error:
        print(str(error), file=sys.stderr)
        return 2
    if args.record and not os.path.isfile(args.record):
        print("no such change record: %s" % args.record, file=sys.stderr)
        return 2
    record = args.record or model.find_change_record(model.Docs(args.docs), args.use_case)
    record = os.path.abspath(record) if record else None
    groups = attribute(view, {args.use_case}, record)
    if args.format == "json":
        print(json.dumps({"use_case": args.use_case, "base": args.base, "groups": groups}, indent=2))
    else:
        print("%s  changes since %s" % (args.use_case, args.base))
        notes = {"specification": "the use case's own file",
                 "attributed": "carries the use case id or names a deletion in the record; check each hunk against the plan",
                 "tracking": "root A-files kept in step with the change",
                 "other-spec": "another specification changed; is that part of this change?",
                 "unattributed": "changed, not part of this change"}
        for group in groups:
            print("\n%s (%d): %s" % (group, len(groups[group]), notes[group]))
            for entry in groups[group]:
                print("  %-9s %s" % (entry["status"], entry["path"]))
        if not any(groups.values()):
            print("\nno changes")
    return 1 if args.strict and groups["unattributed"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
