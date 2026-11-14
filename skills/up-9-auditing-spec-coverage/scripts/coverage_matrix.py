#!/usr/bin/env python3
"""Start the coverage matrix of one use case from the identifiers found in code and tests.

For every unit of the specification (steps, alternative flows, business rules,
pre- and postconditions, linked non-functional requirements and constraints)
the script reports the evidence that markers give:

  code   lines carrying the qualified rule marker (UC-001 BR-002), and the
         files that carry the use case id at all
  tests  lines in files carrying the use case id that name the unit (main, A1, BR-002)

and it lists markers that name a flow or rule the specification does not have.

On a project recovered from code, markers usually do not exist yet. The
recovery ledger (DIR/recovery/ledger.md) then gives, per flow and rule, the
code location it was recovered from; those locations are shown as a third kind
of evidence: where to read, not proof.

A marker right above a function that no other code refers to is reported as a
warning: the rule is enforced where that function is called, if anywhere.

A marker is a claim, not proof. The matrix is finished by reading the code and
the tests it points to; units without a label (steps, postconditions) can only
be judged that way.

Exit code 0, 1 when a file cannot be read, 2 on usage errors, 5 on earlier
specification formats.

Usage:
    coverage_matrix.py UC-001 [--docs DIR] [--code DIR] [--tests DIR ...] [--ledger FILE] [--format md|json]
    coverage_matrix.py --all [--docs DIR] [--code DIR] [--tests DIR ...] [--ledger FILE] [--format md|json]

--ledger defaults to DIR/recovery/ledger.md when that file exists. Give --tests
once for each folder when the tests live in several. --all gives the matrix of
every use case that is not Obsolete, in identifier order, each as a call naming
it would print it; the JSON holds them under use_cases.

Requires Python 3.9+, standard library only. Reads files as data; writes nothing.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model  # noqa: E402  (local module, same folder)


def under(path, folder):
    return folder and os.path.abspath(path).startswith(os.path.abspath(folder) + os.sep)


def under_any(path, folders):
    return any(under(path, folder) for folder in folders or [])


# The code read once per run for the uncalled-marker check: (code_dir, docs_dir, tests) -> (texts, lines by path).
_CODE = {}


def code_texts(code_dir, docs_dir, tests):
    key = (code_dir, docs_dir, tuple(tests or []))
    if key not in _CODE:
        texts, cache = [], {}
        for path in model.iter_source_files(code_dir):
            if under(path, docs_dir) or under_any(path, tests):
                continue
            try:
                cache[path] = model.read_lines(path)
            except (OSError, UnicodeDecodeError):
                continue
            texts.append("\n".join(cache[path]))
        _CODE[key] = (texts, cache)
    return _CODE[key]


def ledger_locations(path, uc_id):
    """Element (UC-001 A1, UC-001 BR-002) -> evidence locations from the recovery ledger."""
    found = {}
    if not path or not os.path.isfile(path):
        return found
    for table in model.read_tables(model.read_lines(path)):
        if not table["header"] or table["header"][0].strip().lower() != "element":
            continue
        for _, row, _ in table["rows"]:
            element = row.get(table["header"][0], "").strip().strip("`")
            match = re.fullmatch(r"%s\s+(A\d+|BR-\d{3})" % re.escape(uc_id), element)
            if match:
                found[match.group(1)] = [e.strip().strip("`") for e in row.get("Evidence", "").split(";") if e.strip()]
    return found


def uncalled_markers(code_dir, docs_dir, tests, rule_hits):
    """Rule -> [(path:line, function name)] for markers right above a function nothing else refers to."""
    texts, cache = code_texts(code_dir, docs_dir, tests)
    found = {}
    for rule, hits in rule_hits.items():
        for path, line in hits:
            name = model.marked_definition(cache.get(path, []), line - 1)
            if name and model.count_references(name, texts) <= 1:
                found.setdefault(rule, []).append(("%s:%d" % (os.path.relpath(path), line), name))
    return found


def build(uc, docs_dir, code_dir, tests, ledger=None):
    """Return (rows, code files, test files, stale markers); tests is a list of folders, or a single folder."""
    if isinstance(tests, str):
        tests = [tests]
    located = ledger_locations(ledger, uc.id)
    rule_ids = {r.id for r in uc.rules}
    flow_numbers = {int(f.label[1:]) for f in uc.flows if re.fullmatch(r"A\d+", f.label)}
    code_files, rule_hits, stale = [], {}, []
    qualified = re.compile(r"%s\s+(BR-\d{3})" % re.escape(uc.id))
    if code_dir:
        for path, line, text in model.find_markers(code_dir, uc.id):
            if under(path, docs_dir) or under_any(path, tests):
                continue
            if path not in code_files:
                code_files.append(path)
            for match in qualified.finditer(text):
                rule = match.group(1)
                if rule in rule_ids:
                    rule_hits.setdefault(rule, []).append((path, line))
                else:
                    stale.append((path, line, "code marks %s %s, which the specification does not define" % (uc.id, rule)))
    uncalled = uncalled_markers(code_dir, docs_dir, tests, rule_hits) if code_dir else {}
    test_files, test_hits = ([], {})
    if tests:
        test_files, test_hits = model.scan_units_in(tests, uc)
        for path in test_files:
            try:
                lines = model.read_lines(path)
            except (OSError, UnicodeDecodeError):
                continue
            for number, text in enumerate(lines, 1):
                for match in re.finditer(r"(?<![A-Za-z0-9])BR[-_ ]?(\d{3})(?!\d)", text, re.IGNORECASE):
                    if "BR-" + match.group(1) not in rule_ids:
                        stale.append((path, number, "test names BR-%s, which the specification does not define" % match.group(1)))
                for match in re.finditer(r"(?<![A-Za-z0-9])A(\d+)(?=[_:])", text, re.IGNORECASE):
                    if int(match.group(1)) not in flow_numbers:
                        stale.append((path, number, "test names A%s, which the specification does not have" % match.group(1)))
    rows = []
    for unit in model.coverage_units(uc):
        label, kind = unit["unit"], unit["kind"]
        code = ["%s:%d" % (os.path.relpath(p), n) for p, n in rule_hits.get(label, [])]
        tests = ["%s:%d" % (os.path.relpath(p), n) for p, n, _ in test_hits.get(label, [])]
        recovered = located.get(label, [])
        if kind == "rule":
            if code and tests:
                note = "marker and test found; confirm by reading"
            elif code:
                note = "TEST MISSING: no test names this rule"
            elif tests:
                note = "MARKER MISSING: no code carries the rule marker"
            else:
                note = "OPEN: no marker, no test"
            if not code and recovered:
                note += "; the ledger locates it, read there"
            for where, name in uncalled.get(label, []):
                note += "; WARNING: the marker at %s sits on %s(), which no other code refers to" % (where, name)
        elif kind in ("scenario", "flow"):
            note = "test found; confirm by reading" if tests else "TEST MISSING: no test names this unit"
            if recovered:
                note += "; the ledger locates it, read there"
        else:
            note = "judge by reading the code and tests of this use case"
        rows.append({"unit": label, "kind": kind, "text": unit["text"], "spec_line": unit["line"],
                     "code": code, "tests": tests, "ledger": recovered, "from_markers": note})
    return rows, code_files, test_files, stale


def matrix_of(uc, path, args, ledger):
    """What one call prints for a use case, as data."""
    rows, code_files, test_files, stale = build(uc, args.docs, args.code, args.tests, ledger)
    return {"use_case": uc.id, "name": uc.name, "status": uc.status, "specification": os.path.relpath(path),
            "code_files": [os.path.relpath(f) for f in code_files], "test_files": [os.path.relpath(f) for f in test_files],
            "rows": rows, "stale_markers": [{"path": os.path.relpath(p), "line": n, "message": m} for p, n, m in stale]}


def print_markdown(result, args):
    rows = result["rows"]
    has_ledger = any(row["ledger"] for row in rows)
    uc_id = result["use_case"]
    print("## %s %s: evidence from markers" % (uc_id, result["name"]))
    print()
    print("Specification: %s, Status %s" % (result["specification"], result["status"]))
    print("Code files carrying %s: %s" % (uc_id, ", ".join(result["code_files"]) or ("none" if args.code else "not searched")))
    print("Test files carrying %s: %s" % (uc_id, ", ".join(result["test_files"]) or ("none" if args.tests else "not searched")))
    print()
    if has_ledger:
        print("| Unit | Description | Code evidence | Test evidence | Recovered from (ledger) | From markers |")
        print("|---|---|---|---|---|---|")
    else:
        print("| Unit | Description | Code evidence | Test evidence | From markers |")
        print("|---|---|---|---|---|")
    for row in rows:
        cells = [row["unit"], row["text"].replace("|", "/")[:70], ", ".join(row["code"]) or "—", ", ".join(row["tests"]) or "—"]
        if has_ledger:
            cells.append(", ".join(row["ledger"]) or "—")
        print("| %s |" % " | ".join(cells + [row["from_markers"]]))
    print()
    print("### Markers without a counterpart in the specification")
    print()
    if result["stale_markers"]:
        for stale in result["stale_markers"]:
            print("- %s:%d  %s" % (stale["path"], stale["line"], stale["message"]))
    else:
        print("- none")


def main(argv):
    parser = argparse.ArgumentParser(description="Start the coverage matrix of a use case from markers.")
    parser.add_argument("use_case", nargs="?", help="identifier, for example UC-001")
    parser.add_argument("--all", action="store_true", help="every use case that is not Obsolete, in one call")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--code", help="folder with the implementation")
    parser.add_argument("--tests", action="append", help="folder with the tests; give it once for each folder")
    parser.add_argument("--ledger", help="recovery ledger (default: <docs>/recovery/ledger.md when it exists)")
    parser.add_argument("--format", choices=("md", "json"), default="md")
    args = parser.parse_args(argv)
    args.docs = args.docs or model.docs_default()
    docs_model = model.Docs(args.docs)
    # A list or a measure cannot be made without the file: an unreadable one stops it with 1.
    stop = model.stop_if_old(docs_model, strict=True)
    if stop:
        return stop
    if args.all == bool(args.use_case):
        print("name one use case or give --all, not both", file=sys.stderr)
        return 2
    if args.use_case and not re.fullmatch(r"UC-\d{3}", args.use_case):
        print("use case identifier must look like UC-001", file=sys.stderr)
        return 2
    reason = args.ledger and model.why_unreadable(args.ledger)
    if reason:
        # A ledger there as a link that cannot be resolved, or behind one or a folder that cannot be searched, is
        # unreadable, not missing; the matrix needs it.
        print("%s:0: ERROR UNREADABLE: cannot read: %s" % (args.ledger, reason), file=sys.stderr)
        return 1
    for folder in [args.docs, args.code] + (args.tests or []):
        if folder and not os.path.isdir(folder):
            print(model.no_such("folder", folder), file=sys.stderr)
            return 2
    path = None if args.all else model.find_use_case(model.Docs(args.docs), args.use_case)
    if not args.all and not path:
        print("no specification file for %s under %s: an audit needs the specification, never one reconstructed from code" % (args.use_case, args.docs), file=sys.stderr)
        return 2
    try:
        if args.all:
            chosen = [(found, uc) for _, found, uc in model.every_use_case(model.Docs(args.docs), obsolete=False)]
        else:
            chosen = [(path, model.parse_use_case(path))]
    except (OSError, UnicodeDecodeError) as exc:
        print("cannot read %s: %s" % (path or getattr(exc, "filename", None) or args.docs, exc), file=sys.stderr)
        return 2
    ledger = args.ledger or os.path.join(args.docs, "recovery", "ledger.md")
    if args.ledger and not os.path.isfile(args.ledger):
        print("no such file: %s" % args.ledger, file=sys.stderr)
        return 2
    results = [matrix_of(uc, found, args, ledger) for found, uc in chosen]
    if args.format == "json":
        model.print_data({"use_cases": results} if args.all else results[0])
        return 0
    for number, result in enumerate(results):
        if number:
            print()
        print_markdown(result, args)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
