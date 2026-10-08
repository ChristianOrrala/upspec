#!/usr/bin/env python3
"""List the flows and rules a specification changed during a change that its change record does not name.

A change record says what a change does to a use case. When the specification
also changes a flow or a rule the record does not name (a correction made on a
reviewer's warning, a flow tidied while editing), that change reaches the code
with no difference from today, no source and no pin, and no later check sees it,
because they all read their list from the record. This script compares the
specification as it was when the change began with the working tree and lists
every flow (A1) and rule (BR-001) that was added, changed or removed but that no
part of the record names: its element metadata, or a cell of an Element or Lives in
column (differences from today, sources, assumptions, owner's decisions).

When the change began: the parent of the commit that added the change record;
while the record is not committed yet, the last commit (HEAD). --since overrides it.

Only flows and rules are compared, the units the rest of the gate tracks; a
changed main step, precondition or postcondition is left to the reviewer.

Exit code 0 when every changed flow and rule is named in the record, 1 when some
are not, 2 on usage errors, 3 when it cannot tell: no change record, no git, or a
specification that did not exist when the change began (a new use case is all
change, and its sources table covers it).

Usage:
    unrecorded_changes.py UC-012 [--docs DIR] [--record FILE] [--since REF] [--format text|json]

Requires Python 3.9+, standard library only, and git. Reads only; changes nothing.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model  # noqa: E402  (local module, same folder)

UNIT = re.compile(r"\b(A\d+|BR-\d{3})\b")


class Undecidable(Exception):
    """The comparison cannot be made; the message says why."""


def find_spec(docs, uc_id):
    for path in docs.use_case_files():
        name = os.path.basename(path)
        if name == uc_id + ".md" or name.startswith(uc_id + "-"):
            return path
    return None


def units_for(text, uc_id):
    """Flows and rules a cell names for this use case: those after a mention of it, and those before
    any use case is named (the cell belongs to the change as a whole). Units after another use case's
    identifier are that use case's."""
    found, owner = set(), None
    for token in re.finditer(r"\bUC-\d{3}\b|\bA\d+\b|\bBR-\d{3}\b", text):
        value = token.group(0)
        if value.startswith("UC-"):
            owner = value
        elif owner in (None, uc_id):
            found.add(value)
    return found


def recorded_units(path, uc_id):
    """Every flow and rule the record names for this use case."""
    named = set()
    named |= units_for(model.parse_change_record(path).element, uc_id)
    lines = model.read_lines(path)
    for table in model.read_tables(lines):
        header = [h.strip().lower() for h in table["header"]]
        columns = [table["header"][i] for i, h in enumerate(header) if h.startswith("element") or h == "lives in"]
        for _, row, _ in table["rows"]:
            for column in columns:
                cell = row.get(column, "").strip()
                if cell and not cell.startswith("["):
                    named |= units_for(cell, uc_id)
    return named


def names_use_case(path, uc_id):
    if uc_id in model.RE_UC_ID.findall(model.parse_change_record(path).element):
        return True
    for table in model.read_tables(model.read_lines(path)):
        if any(h.strip().lower().startswith("element") for h in table["header"]):
            if any(uc_id in " ".join(row.values()) for _, row, _ in table["rows"]):
                return True
    return False


def find_record(docs_dir, uc_id):
    """The newest change record named after the use case or naming it; None when there is none."""
    found = []
    for path in model.Docs(docs_dir).change_record_files():
        name = os.path.basename(path)
        if name == uc_id + ".md" or name.startswith(uc_id + "-") or names_use_case(path, uc_id):
            found.append(path)
    return max(found, key=lambda path: (os.path.getmtime(path), path)) if found else None


def change_start(repo, record_rel):
    """The commit the change began from: the parent of the commit that added the record, or HEAD
    while the record is not committed."""
    code, _ = model.git(["ls-files", "--error-unmatch", "--", record_rel], cwd=repo)
    if code != 0:
        code, out = model.git(["rev-parse", "--verify", "HEAD"], cwd=repo)
        if code != 0:
            raise Undecidable("nothing is committed yet")
        return out.strip()
    code, out = model.git(["log", "--follow", "--diff-filter=A", "--format=%H", "--", record_rel], cwd=repo)
    added = out.split() if code == 0 else []
    if not added:
        raise Undecidable("git has no commit that added %s" % record_rel)
    code, out = model.git(["rev-parse", "--verify", "%s^" % added[-1]], cwd=repo)
    if code != 0:
        raise Undecidable("the change record came with the first commit; pass --since")
    return out.strip()


def check(docs_dir, uc_id, record=None, since=None):
    """{use_case, record, since, changed, recorded, unrecorded}; raises Undecidable."""
    docs = model.Docs(docs_dir)
    path = find_spec(docs, uc_id)
    if not path:
        raise SystemExit("no specification file for %s under %s" % (uc_id, docs_dir))
    record = record or find_record(docs_dir, uc_id)
    if not record:
        raise Undecidable("no change record names %s" % uc_id)
    code, top = model.git(["rev-parse", "--show-toplevel"], cwd=os.path.dirname(os.path.abspath(path)))
    if code != 0:
        raise Undecidable("not a git repository, or git is not available")
    repo = top.strip()

    def rel(target):
        return os.path.relpath(os.path.realpath(target), os.path.realpath(repo)).replace(os.sep, "/")

    if since:
        code, out = model.git(["rev-parse", "--verify", since + "^{commit}"], cwd=repo)
        if code != 0:
            raise SystemExit("unknown revision: %s" % since)
        start = out.strip()
    else:
        start = change_start(repo, rel(record))
    code, old_text = model.git(["show", "%s:%s" % (start, rel(path))], cwd=repo)
    if code != 0:
        raise Undecidable("%s did not exist when the change began: a new use case is all change" % rel(path))
    old = model.parse_use_case_lines(old_text.split("\n"), rel(path))
    new = model.parse_use_case(path)
    changed = []
    for change in model.compare_use_cases(old, new):
        unit = change["element"].split(" ")[0]
        if UNIT.fullmatch(unit):
            changed.append({"unit": unit, "change": change["change"]})
    recorded = recorded_units(record, uc_id)
    return {"use_case": uc_id, "record": os.path.relpath(record), "since": start,
            "changed": changed, "recorded": sorted(recorded),
            "unrecorded": [c for c in changed if c["unit"] not in recorded]}


def main(argv):
    parser = argparse.ArgumentParser(description="Specification changes a change record does not name.")
    parser.add_argument("use_case", help="identifier, for example UC-012")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--record", help="the change record (default: the newest one naming the use case)")
    parser.add_argument("--since", help="the commit the change began from (default: before the record was added)")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    args.docs = args.docs or model.docs_default()
    if not re.fullmatch(r"UC-\d{3}", args.use_case):
        print("use case identifier must look like UC-012", file=sys.stderr)
        return 2
    if not os.path.isdir(args.docs):
        print("no such folder: %s" % args.docs, file=sys.stderr)
        return 2
    if args.record and not os.path.isfile(args.record):
        print("no such file: %s" % args.record, file=sys.stderr)
        return 2
    docs = model.Docs(args.docs)
    if args.record:
        records = docs.change_record_files()
        docs.change_record_files = lambda: sorted(set(records + [args.record]))
    stop = model.stop_if_old(docs)
    if stop is not None:
        return stop
    try:
        result = check(args.docs, args.use_case, args.record, args.since)
    except Undecidable as exc:
        print("%s: cannot tell: %s" % (args.use_case, exc), file=sys.stderr)
        return 3
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, UnicodeDecodeError) as exc:
        print("%s:0: ERROR UNREADABLE: cannot read: %s" % (args.record or args.docs, exc), file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        def listed(items):
            return ", ".join("%s (%s)" % (c["unit"], c["change"]) for c in items) or "none"
        print("%s  specification changes since %s, against %s" % (result["use_case"], result["since"][:12], result["record"]))
        print("Changed flows and rules: %s" % listed(result["changed"]))
        print("Named in the record:     %s" % (", ".join(result["recorded"]) or "none"))
        print("Not in the record:       %s" % listed(result["unrecorded"]))
        if result["unrecorded"]:
            print("Result: %d change(s) the record does not name: add each to the record (a difference from today "
                  "with its source, or a correction with why) or undo it" % len(result["unrecorded"]))
        else:
            print("Result: every changed flow and rule is in the record")
    return 1 if result["unrecorded"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
