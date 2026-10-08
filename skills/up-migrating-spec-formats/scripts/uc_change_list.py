#!/usr/bin/env python3
"""List what changed in one use case specification since it was last implemented.

Compares an earlier revision of the file with the working tree, element by
element: actors, trigger, requirement links, preconditions, main scenario
steps, alternative flows, postconditions and business rules. The result is the
list of behavior changes that code may be changed for when synchronizing.

Without --base, the earlier revision is the most recent commit in which the
file's Status was Implemented, Tested or Done.

Exit code 0 with a list (possibly empty), 2 on usage errors (no such use case,
not a git repository), 3 when no earlier implemented revision exists (treat the
use case as new).

Usage:
    uc_change_list.py UC-012 [--docs DIR] [--base REF] [--format text|json]

Requires Python 3.9+, standard library only, and git. Reads only; changes nothing.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model  # noqa: E402  (local module, same folder)

IMPLEMENTED_RANK = model.STATUS_RANK["Implemented"]


def find_spec(docs, uc_id):
    for path in docs.use_case_files():
        if os.path.basename(path).startswith(uc_id + "-") or os.path.basename(path) == uc_id + ".md":
            return path
    return None


def revision_text(repo, ref, rel_path):
    code, out = model.git(["show", "%s:%s" % (ref, rel_path)], cwd=repo)
    return out if code == 0 else None


def find_base(repo, rel_path):
    """Most recent commit in which the file's Status was Implemented or later."""
    code, out = model.git(["log", "--format=%H", "--", rel_path], cwd=repo)
    if code != 0:
        return None
    for sha in out.split():
        text = revision_text(repo, sha, rel_path)
        if text is None:
            continue
        status = model.parse_use_case_lines(text.split("\n"), rel_path).status
        if model.STATUS_RANK.get(status, -1) >= IMPLEMENTED_RANK:
            return sha
    return None


# The comparison lives in spec_model, shared with the review's and the finish check's
# check for specification changes a change record does not name.
norm = model.norm_text
compare = model.compare_use_cases


def main(argv):
    parser = argparse.ArgumentParser(description="List what changed in a use case specification since it was last implemented.")
    parser.add_argument("use_case", help="identifier, for example UC-012")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--base", help="revision to compare against (default: last revision with Status Implemented or later)")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    args.docs = args.docs or model.docs_default()
    stop = model.stop_if_old(model.Docs(args.docs))
    if stop is not None:
        return stop
    if not re.fullmatch(r"UC-\d{3}", args.use_case):
        print("use case identifier must look like UC-012", file=sys.stderr)
        return 2
    if not os.path.isdir(args.docs):
        print("no such folder: %s" % args.docs, file=sys.stderr)
        return 2
    path = find_spec(model.Docs(args.docs), args.use_case)
    if not path:
        print("no specification file for %s under %s" % (args.use_case, args.docs), file=sys.stderr)
        return 2
    folder = os.path.dirname(os.path.abspath(path))
    code, top = model.git(["rev-parse", "--show-toplevel"], cwd=folder)
    if code != 0:
        print("not a git repository (or git is not installed): cannot compare revisions; compare the two versions by hand", file=sys.stderr)
        return 2
    repo = top.strip()
    rel = os.path.relpath(os.path.realpath(path), os.path.realpath(repo)).replace(os.sep, "/")
    base = args.base or find_base(repo, rel)
    if not base:
        print("no revision of %s has Status Implemented or later: treat the use case as new" % rel, file=sys.stderr)
        return 3
    old_text = revision_text(repo, base, rel)
    if old_text is None:
        print("%s does not exist at revision %s" % (rel, base), file=sys.stderr)
        return 3 if not args.base else 2
    changes = compare(model.parse_use_case_lines(old_text.split("\n"), rel), model.parse_use_case(path))
    if args.format == "json":
        print(json.dumps({"use_case": args.use_case, "base": base, "file": rel, "changes": changes}, indent=2, ensure_ascii=False))
        return 0
    print("%s  %s  compared with %s" % (args.use_case, rel, base[:12]))
    if not changes:
        print("no behavioral difference: nothing to synchronize")
    for c in changes:
        if c["change"] == "changed":
            print("changed  %-24s %s\n%s-> %s" % (c["element"], c["old"], " " * 31, c["new"]))
        else:
            print("%-8s %-24s %s" % (c["change"], c["element"], c["new"] if c["change"] == "added" else c["old"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
