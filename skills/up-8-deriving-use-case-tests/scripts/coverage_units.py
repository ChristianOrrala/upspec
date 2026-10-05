#!/usr/bin/env python3
"""List the coverage units of one use case and the tests that carry each unit's label.

A unit is something the specification promises: the main success scenario,
each alternative flow, each business rule, each precondition, each success and
failure postcondition, and each linked non-functional requirement or
constraint. The list is the test plan.

With --tests, files under that folder that carry the use case id (UC-006 or
UC006) are scanned for unit labels (main, A1, BR-001) in test names,
annotations and comments. A hit means a test claims the unit; whether it
really covers it is judged by reading the test and by the guard check.

Exit code 0, 2 on usage errors.

Usage:
    coverage_units.py UC-006 [--docs DIR] [--tests DIR] [--format text|json]

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


def find_spec(docs, uc_id):
    for path in docs.use_case_files():
        name = os.path.basename(path)
        if name.startswith(uc_id + "-") or name == uc_id + ".md":
            return path
    return None


def main(argv):
    parser = argparse.ArgumentParser(description="List the coverage units of a use case.")
    parser.add_argument("use_case", help="identifier, for example UC-006")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--tests", help="folder that holds the tests")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    args.docs = args.docs or model.docs_default()
    if not re.fullmatch(r"UC-\d{3}", args.use_case):
        print("use case identifier must look like UC-006", file=sys.stderr)
        return 2
    if not os.path.isdir(args.docs):
        print("no such folder: %s" % args.docs, file=sys.stderr)
        return 2
    if args.tests and not os.path.isdir(args.tests):
        print("no such folder: %s" % args.tests, file=sys.stderr)
        return 2
    path = find_spec(model.Docs(args.docs), args.use_case)
    if not path:
        print("no specification file for %s under %s" % (args.use_case, args.docs), file=sys.stderr)
        return 2
    try:
        uc = model.parse_use_case(path)
    except (OSError, UnicodeDecodeError) as exc:
        print("cannot read %s: %s" % (path, exc), file=sys.stderr)
        return 2
    units = [u for u in model.coverage_units(uc) if u["kind"] != "step"]
    files, hits = ([], {})
    if args.tests:
        files, hits = model.scan_units(args.tests, uc)
    for unit in units:
        unit["labeled"] = unit["kind"] in LABELED
        unit["tests"] = [{"path": os.path.relpath(p), "line": n, "text": t} for p, n, t in hits.get(unit["unit"], [])]
    if args.format == "json":
        print(json.dumps({"use_case": uc.id, "name": uc.name, "status": uc.status, "specification": os.path.relpath(path),
                          "test_files": [os.path.relpath(f) for f in files], "units": units}, indent=2, ensure_ascii=False))
        return 0
    print("%s %s (Status %s)  %s" % (uc.id, uc.name, uc.status, os.path.relpath(path)))
    if args.tests:
        print("test files carrying %s: %s" % (uc.id, ", ".join(os.path.relpath(f) for f in files) or "none"))
    print()
    for unit in units:
        print("%-9s %-22s %s" % (unit["unit"], unit["kind"], unit["text"]))
        if not args.tests:
            continue
        if unit["tests"]:
            for test in unit["tests"]:
                print("%10s%s:%d  %s" % ("", test["path"], test["line"], test["text"][:90]))
        elif unit["labeled"]:
            print("%10sNO TEST carries this label" % "")
        else:
            print("%10s(asserted inside the tests above; judge by reading)" % "")
    if args.tests:
        missing = [u["unit"] for u in units if u["labeled"] and not u["tests"]]
        print("\nlabeled units without a test: %s" % (", ".join(missing) or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
