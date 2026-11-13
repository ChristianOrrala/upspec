#!/usr/bin/env python3
"""List the coverage units of one use case and the tests that carry each unit's label.

A unit is something the specification promises: the main success scenario,
each alternative flow, each business rule, each precondition, each success and
failure postcondition, and each linked non-functional requirement or
constraint. The list is the test plan.

With --tests, files under that folder that carry the use case id (UC-006 or
UC006) are scanned for unit labels (main, A1, BR-001) in test names,
annotations and comments. A hit means a test claims the unit; whether it
really covers it is judged by reading the test and by the guard check. Give
--tests once for each folder when the tests live in several.

--all lists every use case that is not Obsolete, in identifier order, each as
a call naming it would print it; the JSON holds them under use_cases.

Exit code 0, 1 when a file cannot be read, 2 on usage errors, 5 on earlier
specification formats.

Usage:
    coverage_units.py UC-006 [--docs DIR] [--tests DIR ...] [--format text|json]
    coverage_units.py --all [--docs DIR] [--tests DIR ...] [--format text|json]

Requires Python 3.9+, standard library only. Reads files as data; writes nothing.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model  # noqa: E402  (local module, same folder)

# Units whose coverage is claimed by a label in a test; the others are asserted
# inside those tests and can only be judged by reading them.
LABELED = ("scenario", "flow", "rule")


def units_of(uc, path, tests):
    """What one call prints for a use case, as data: its units, each with the tests that carry its label."""
    units = [u for u in model.coverage_units(uc) if u["kind"] != "step"]
    files, hits = ([], {})
    if tests:
        files, hits = model.scan_units_in(tests, uc)
    for unit in units:
        unit["labeled"] = unit["kind"] in LABELED
        unit["tests"] = [{"path": os.path.relpath(p), "line": n, "text": t} for p, n, t in hits.get(unit["unit"], [])]
    return {"use_case": uc.id, "name": uc.name, "status": uc.status, "specification": os.path.relpath(path),
            "test_files": [os.path.relpath(f) for f in files], "units": units}


def print_text(result, tests):
    units = result["units"]
    print("%s %s (Status %s)  %s" % (result["use_case"], result["name"], result["status"], result["specification"]))
    if tests:
        print("test files carrying %s: %s" % (result["use_case"], ", ".join(result["test_files"]) or "none"))
    print()
    for unit in units:
        print("%-9s %-22s %s" % (unit["unit"], unit["kind"], unit["text"]))
        if not tests:
            continue
        if unit["tests"]:
            for test in unit["tests"]:
                print("%10s%s:%d  %s" % ("", test["path"], test["line"], test["text"][:90]))
        elif unit["labeled"]:
            print("%10sNO TEST carries this label" % "")
        else:
            print("%10s(asserted inside the tests above; judge by reading)" % "")
    if tests:
        missing = [u["unit"] for u in units if u["labeled"] and not u["tests"]]
        print("\nlabeled units without a test: %s" % (", ".join(missing) or "none"))


def main(argv):
    parser = argparse.ArgumentParser(description="List the coverage units of a use case.")
    parser.add_argument("use_case", nargs="?", help="identifier, for example UC-006")
    parser.add_argument("--all", action="store_true", help="every use case that is not Obsolete, in one call")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--tests", action="append", help="folder that holds the tests; give it once for each folder")
    parser.add_argument("--format", choices=("text", "json"), default="text")
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
        print("use case identifier must look like UC-006", file=sys.stderr)
        return 2
    if not os.path.isdir(args.docs):
        print("no such folder: %s" % args.docs, file=sys.stderr)
        return 2
    for folder in args.tests or []:
        if not os.path.isdir(folder):
            print("no such folder: %s" % folder, file=sys.stderr)
            return 2
    path = None if args.all else model.find_use_case(model.Docs(args.docs), args.use_case)
    if not args.all and not path:
        print("no specification file for %s under %s" % (args.use_case, args.docs), file=sys.stderr)
        return 2
    try:
        if args.all:
            chosen = [(found, uc) for _, found, uc in model.every_use_case(model.Docs(args.docs), obsolete=False)]
        else:
            chosen = [(path, model.parse_use_case(path))]
    except (OSError, UnicodeDecodeError) as exc:
        print("cannot read %s: %s" % (path or getattr(exc, "filename", None) or args.docs, exc), file=sys.stderr)
        return 2
    results = [units_of(uc, path, args.tests) for path, uc in chosen]
    if args.format == "json":
        print(json.dumps({"use_cases": results} if args.all else results[0], indent=2, ensure_ascii=False))
        return 0
    for number, result in enumerate(results):
        if number:
            print()
        print_text(result, args.tests)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
