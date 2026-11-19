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

Exit code 0 when it ran, whether or not every changed flow and rule is named in
the record, an unreadable file included (with --strict 1 when some are not or a
file is unreadable), 2 on usage errors, 3 when it
cannot tell: no git, nothing committed, or a
specification that did not exist when the change began (a new use case is all
change, and its sources table covers it); 4 when no change record names the
use case and it could run (without git or a commit it is 3, whether or not a
record names the use case).

--all answers for every use case with an identifier, in identifier order, in
one call: each with its state (compared, no_record, cannot_tell or unreadable),
its reason when it was not compared, and what one call reports when it was.
A use case file that cannot be read is an unreadable entry under the identifier
its file name carries, and the others are still answered; every file that
cannot be read is also the finding UNREADABLE on standard error.
A use case without a change record is a state there, not an exit code. --all
exits 0 when it ran (with --strict 1 when some change is not named or a file
is unreadable), 3 outside a git repository, and refuses --record. A
specification folder that is a link that cannot be resolved is the finding
UNREADABLE, before git is asked, with nothing on standard output (exit 0, with
--strict 1).

Usage:
    unrecorded_changes.py UC-012 [--docs DIR] [--record FILE] [--since REF] [--format text|json] [--strict]
    unrecorded_changes.py --all [--docs DIR] [--since REF] [--format text|json] [--strict]

Requires Python 3.9+, standard library only, and git. Reads only; changes nothing, not even a bytecode cache beside
an installed copy.
"""
import argparse
import os
import re
import sys

sys.dont_write_bytecode = True   # a __pycache__ folder beside an installed copy would be a file this command wrote
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model  # noqa: E402  (local module, same folder)

# the release these copies belong to; hook_gate.py refuses siblings of another release
UPSPEC_VERSION = "2.1.1"

UNIT = re.compile(r"\b(A\d+|BR-\d{3})\b")


# The exit code of a run for one use case that no change record names, apart from 3 (cannot tell).
NO_RECORD_EXIT = 4


class Undecidable(Exception):
    """The comparison cannot be made; the message says why."""


class NoRecord(Undecidable):
    """No change record names the use case: there is nothing to compare it with."""


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
    path = model.find_use_case(docs, uc_id)
    if not path:
        raise SystemExit("no specification file for %s under %s" % (uc_id, docs_dir))
    record = record or find_record(docs_dir, uc_id)
    # Could not run wins over no record: without git, or without a commit to compare with, the answer is 3.
    code, top = model.git(["rev-parse", "--show-toplevel"], cwd=os.path.dirname(os.path.abspath(path)))
    if code != 0:
        raise Undecidable("not a git repository, or git is not available")
    repo = top.strip()
    if not record:
        if model.git(["rev-parse", "--verify", "HEAD"], cwd=repo)[0] != 0:
            raise Undecidable("nothing is committed yet")
        raise NoRecord("no change record names %s" % uc_id)

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


def cannot_read(exc, path=None):
    """The reason of an unreadable entry: the file, when known, and the error."""
    path = getattr(exc, "spec_path", None) or path
    if not path:
        return "cannot read: %s" % exc
    return "cannot read %s: %s" % (os.path.relpath(path).replace(os.sep, "/"), exc)


def check_all(docs_dir, since=None, unreadable=None):
    """[{use_case, state, reason, record, since, changed, recorded, unrecorded}] for every identified use case.

    A use case file that cannot be read is an entry in the state unreadable, under the identifier its file name
    carries, beside the others; unreadable, a list, receives each such file as (path, error)."""
    unreadable = [] if unreadable is None else unreadable
    results = []
    blank = {"state": "compared", "reason": None, "record": None, "since": None,
             "changed": [], "recorded": [], "unrecorded": []}
    for uc_id, _, _ in model.every_use_case(model.Docs(docs_dir), unreadable=unreadable):
        entry = dict(blank, use_case=uc_id)
        try:
            entry.update(check(docs_dir, uc_id, None, since))
        except NoRecord as exc:
            entry.update(state="no_record", reason=str(exc))
        except Undecidable as exc:
            entry.update(state="cannot_tell", reason=str(exc))
        except SystemExit as exc:
            entry.update(state="cannot_tell", reason=str(exc))
        except (OSError, UnicodeDecodeError) as exc:
            entry.update(state="unreadable", reason=cannot_read(exc))
        results.append(entry)
    for path, exc in unreadable:
        named = model.RE_UC_ID.search(os.path.basename(path))
        results.append(dict(blank, use_case=named.group(0) if named else os.path.basename(path), state="unreadable",
                            reason=cannot_read(exc, path)))
    results.sort(key=lambda entry: entry["use_case"])
    return [{key: entry[key] for key in ("use_case",) + tuple(blank)} for entry in results]


def listed(items):
    return ", ".join("%s (%s)" % (c["unit"], c["change"]) for c in items) or "none"


def main_all(args):
    """--all: every use case in one call."""
    code, _ = model.git(["rev-parse", "--show-toplevel"], cwd=os.path.abspath(args.docs))
    if code != 0:
        print("cannot tell: not a git repository, or git is not available", file=sys.stderr)
        return 3
    if args.since:
        code, _ = model.git(["rev-parse", "--verify", args.since + "^{commit}"], cwd=os.path.abspath(args.docs))
        if code != 0:
            print("unknown revision: %s" % args.since, file=sys.stderr)
            return 2
    unreadable = []
    try:
        results = check_all(args.docs, args.since, unreadable)
    except (OSError, UnicodeDecodeError) as exc:
        print("%s:0: ERROR UNREADABLE: cannot read: %s" % (args.docs, exc), file=sys.stderr)
        return 1 if args.strict else 0
    # Every file that could not be read, a use case's or another's, is the finding UNREADABLE.
    reported = set()
    for path, exc in args.unreadable + unreadable:
        rel = os.path.relpath(path).replace(os.sep, "/")
        if rel not in reported:
            reported.add(rel)
            print("%s:0: ERROR UNREADABLE: cannot read: %s" % (rel, exc), file=sys.stderr)
    if args.format == "json":
        model.print_data({"use_cases": results})
    else:
        for entry in results:
            if entry["state"] == "compared":
                print("%s  against %s since %s: not in the record: %s" % (entry["use_case"], entry["record"],
                                                                          entry["since"][:12], listed(entry["unrecorded"])))
            else:
                print("%s  %s: %s" % (entry["use_case"], entry["state"].replace("_", " "), entry["reason"]))
        unnamed = [entry["use_case"] for entry in results if entry["unrecorded"]]
        print("Result: %s" % ("%d use case(s) with changes their record does not name: %s" % (len(unnamed), ", ".join(unnamed))
                              if unnamed else "every compared use case's changed flows and rules are in its record"))
    failed = reported or any(entry["unrecorded"] or entry["state"] == "unreadable" for entry in results)
    return 1 if failed and args.strict else 0


def main(argv):
    parser = argparse.ArgumentParser(description="Specification changes a change record does not name.")
    parser.add_argument("use_case", nargs="?", help="identifier, for example UC-012")
    parser.add_argument("--all", action="store_true", help="every use case with an identifier, in one call")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--record", help="the change record (default: the newest one naming the use case)")
    parser.add_argument("--since", help="the commit the change began from (default: before the record was added)")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--strict", action="store_true", help="exit 1 when it finds problems (default: exit 0, the findings are reported)")
    args = parser.parse_args(argv)
    args.docs = args.docs or model.docs_default()
    if args.all == bool(args.use_case):
        print("name one use case or give --all, not both", file=sys.stderr)
        return 2
    if args.all and args.record:
        print("--record names the record of one use case; it does not go with --all", file=sys.stderr)
        return 2
    if args.use_case and not re.fullmatch(r"UC-\d{3}", args.use_case):
        print("use case identifier must look like UC-012", file=sys.stderr)
        return 2
    if not model.folder_present(args.docs):
        print("no such folder: %s" % args.docs, file=sys.stderr)
        return 2
    # A record there as a link that cannot be resolved is not missing: the old-format check names it as UNREADABLE.
    if args.record and (os.path.isdir(args.record) or model.absent(args.record)):
        print("no such file: %s" % args.record, file=sys.stderr)
        return 2
    docs = model.Docs(args.docs)
    if args.record:
        records = docs.change_record_files()
        docs.change_record_files = lambda: sorted(set(records + [args.record]))
    # --all answers for every use case: a file that cannot be read is an entry in the state unreadable, so it does not
    # stop the run; an earlier format in any other file still does.
    args.unreadable = [] if args.all else None
    stop = model.stop_if_old(docs, strict=args.strict, unreadable=args.unreadable)
    if stop is not None:
        return stop
    if args.all and not os.path.isdir(args.docs):
        # The specification folder itself cannot be read (a link that cannot be resolved): there is no use case to
        # answer for, and git is not asked about a folder that is not there.
        for path, exc in args.unreadable:
            print("%s:0: ERROR UNREADABLE: cannot read: %s" % (path, exc), file=sys.stderr)
        return 1 if args.strict else 0
    if args.all:
        return main_all(args)
    try:
        result = check(args.docs, args.use_case, args.record, args.since)
    except NoRecord as exc:
        print("%s: cannot tell: %s" % (args.use_case, exc), file=sys.stderr)
        return NO_RECORD_EXIT
    except Undecidable as exc:
        print("%s: cannot tell: %s" % (args.use_case, exc), file=sys.stderr)
        return 3
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, UnicodeDecodeError) as exc:
        print("%s:0: ERROR UNREADABLE: cannot read: %s" % (args.record or args.docs, exc), file=sys.stderr)
        # An unreadable file is a finding like the others.
        return 1 if args.strict else 0
    if args.format == "json":
        model.print_data(result)
    else:
        print("%s  specification changes since %s, against %s" % (result["use_case"], result["since"][:12], result["record"]))
        print("Changed flows and rules: %s" % listed(result["changed"]))
        print("Named in the record:     %s" % (", ".join(result["recorded"]) or "none"))
        print("Not in the record:       %s" % listed(result["unrecorded"]))
        if result["unrecorded"]:
            print("Result: %d change(s) the record does not name: add each to the record (a difference from today "
                  "with its source, or a correction with why) or undo it" % len(result["unrecorded"]))
        else:
            print("Result: every changed flow and rule is in the record")
    # The unnamed changes are the output; only a strict run turns them into a failure.
    return 1 if result["unrecorded"] and args.strict else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
