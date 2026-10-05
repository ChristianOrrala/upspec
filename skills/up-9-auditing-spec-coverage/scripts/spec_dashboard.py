#!/usr/bin/env python3
"""Generate the spec dashboard: two Markdown tables of specified, implemented and verified behavior.

Table 1, high-level progress: functional requirements, use cases, use cases
with full test coverage, regression stability.
Table 2, one row per use case: linked requirements, Status, code, unit tests,
end-to-end, regression, integrity.

Everything is computed from the repository: Status fields, Requirements lines,
identifiers found in code and tests, journey test cases, and a test report when
one is given. Nothing is typed by hand, so the dashboard cannot drift from the
project. The rules behind every cell are printed under the tables.

Exit code 0, 2 on usage errors.

Usage:
    spec_dashboard.py [--docs DIR] [--code DIR] [--tests DIR] [--junit FILE]

--junit is a test report in JUnit XML (most test runners can write one). Without
it, regression stability is reported as unknown, never assumed.

Requires Python 3.9+, standard library only. Reads files as data; prints to standard output.
"""
import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model  # noqa: E402  (local module, same folder)

FORBIDDEN = re.compile(rb"<!\s*(DOCTYPE|ENTITY)", re.IGNORECASE)
TESTED = model.STATUS_RANK["Tested"]
IMPLEMENTED = model.STATUS_RANK["Implemented"]
APPROVED = model.STATUS_RANK["Approved"]


def under(path, folder):
    return folder and os.path.abspath(path).startswith(os.path.abspath(folder) + os.sep)


def read_junit(path):
    """Return (tests, failed) from a JUnit XML report, or raise ValueError."""
    with open(path, "rb") as handle:
        data = handle.read()
    if FORBIDDEN.search(data):
        raise ValueError("the report has a document type or entity declaration and was not parsed")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError("not well-formed XML: %s" % exc)
    suites = [root] if root.tag == "testsuite" else [e for e in root.iter("testsuite")]
    tests = failed = 0
    for suite in suites:
        tests += int(suite.get("tests", 0) or 0)
        failed += int(suite.get("failures", 0) or 0) + int(suite.get("errors", 0) or 0)
    if not suites:
        raise ValueError("no testsuite element found")
    return tests, failed


def percent(part, total):
    return "%d%%" % round(100.0 * part / total) if total else "—"


def main(argv):
    parser = argparse.ArgumentParser(description="Generate the spec dashboard.")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--code", help="folder with the implementation")
    parser.add_argument("--tests", help="folder with the tests")
    parser.add_argument("--junit", help="test report in JUnit XML")
    args = parser.parse_args(argv)
    args.docs = args.docs or model.docs_default()
    for folder in (args.docs, args.code, args.tests):
        if folder and not os.path.isdir(folder):
            print("no such folder: %s" % folder, file=sys.stderr)
            return 2
    regression = None
    if args.junit:
        try:
            regression = read_junit(args.junit)
        except (OSError, ValueError) as exc:
            print("cannot use the test report %s: %s" % (args.junit, exc), file=sys.stderr)
            return 2
    docs = model.Docs(args.docs)
    try:
        requirements = model.parse_requirements(docs.requirements)[0] if docs.requirements else []
        use_cases = [u for u in model.load_use_cases(docs) if u.id and u.status != "Obsolete"]
        diagram = model.parse_diagram(docs.diagram) if docs.diagram else None
        journeys = [model.parse_test_case(p) for p in docs.test_case_files()]
    except (OSError, UnicodeDecodeError) as exc:
        print("cannot read the specifications: %s" % exc, file=sys.stderr)
        return 2
    by_id = {u.id: u for u in use_cases}
    pending = sorted(i for i in (diagram.use_cases if diagram else {}) if i not in by_id)

    rows = []
    full_tests = some_tests = 0
    for uc in use_cases:
        rank = model.STATUS_RANK.get(uc.status, -1)
        code = "not searched"
        if args.code:
            hits = [p for p, _, _ in model.find_markers(args.code, uc.id) if not under(p, args.docs) and not under(p, args.tests)]
            code = "yes" if hits else "no"
        unit = "not searched"
        if args.tests:
            labeled = ["Main"] + [f.label for f in uc.flows] + [r.id for r in uc.rules]
            _, hits = model.scan_units(args.tests, uc)
            found = [label for label in labeled if hits.get(label)]
            unit = "yes" if len(found) == len(labeled) else ("partial" if found else "no")
            full_tests += unit == "yes"
            some_tests += unit == "partial"
        chained = [tc for tc in journeys if uc.id in tc.use_case_ids() and tc.field("Status").split("|")[0].strip() != "Obsolete"]
        if any(tc.field("Status").split("|")[0].strip() == "Automated" for tc in chained):
            e2e = "yes"
        elif chained:
            e2e = "planned"
        else:
            e2e = "no"
        if regression is None:
            stable = "unknown"
        else:
            stable = "yes" if regression[1] == 0 else "no"
        evidence = [code == "yes", unit == "yes", e2e == "yes"]
        if rank >= APPROVED and all(evidence) and stable != "no":
            integrity = "Strong"
        elif not any(evidence) and unit != "partial" and e2e != "planned":
            integrity = "Weak"
        else:
            integrity = "Partial"
        frs = ", ".join(r for r in uc.requirement_ids if r.startswith("FR-")) or "—"
        rows.append([uc.id, uc.name, frs, uc.status, code, unit, e2e, stable, integrity])

    linking = {}
    for uc in use_cases:
        for rid in uc.requirement_ids:
            linking.setdefault(rid, []).append(uc)
    frs = [r for r in requirements if r.kind == "FR" and r.status not in model.REQ_SCOPE]
    fr_complete = sum(1 for r in frs if linking.get(r.id) and all(model.STATUS_RANK.get(u.status, -1) >= TESTED for u in linking[r.id]))
    fr_none = sum(1 for r in frs if not linking.get(r.id))
    uc_total = len(use_cases) + len(pending)
    uc_complete = sum(1 for u in use_cases if model.STATUS_RANK.get(u.status, -1) >= TESTED)

    print("# Spec Dashboard")
    print()
    print("Generated from the repository. Do not edit by hand; run the script again.")
    print()
    print("## Progress")
    print()
    print("| Category | Total | Complete | In progress | Not started | Coverage |")
    print("|---|---|---|---|---|---|")
    print("| Functional requirements | %d | %d | %d | %d | %s |" % (len(frs), fr_complete, len(frs) - fr_complete - fr_none, fr_none, percent(fr_complete, len(frs))))
    print("| Use cases | %d | %d | %d | %d | %s |" % (uc_total, uc_complete, len(use_cases) - uc_complete, len(pending), percent(uc_complete, uc_total)))
    if args.tests:
        print("| Use cases with full test coverage | %d | %d | %d | %d | %s |" % (uc_total, full_tests, some_tests, uc_total - full_tests - some_tests, percent(full_tests, uc_total)))
    else:
        print("| Use cases with full test coverage | %d | — | — | — | not searched |" % uc_total)
    if regression is None:
        print("| Regression stability | — | — | — | — | unknown: no test report given |")
    else:
        passed = regression[0] - regression[1]
        print("| Regression stability | %d tests | %d passed | — | %d failed | %s |" % (regression[0], passed, regression[1], "Stable" if regression[1] == 0 else "Regressed"))
    print()
    print("## Use cases")
    print()
    print("| Use case | Name | Linked FR | Status | Code | Unit | E2E | Regression | Integrity |")
    print("|---|---|---|---|---|---|---|---|---|")
    for row in rows:
        print("| " + " | ".join(row) + " |")
    for uc_id in pending:
        print("| %s | %s | — | not specified | no | no | no | — | Weak |" % (uc_id, diagram.use_cases[uc_id][0]))
    print()
    print("## How the cells are computed")
    print()
    print("- Requirement complete: every use case that links it is Tested or Done. Not started: no use case links it. Deferred and Rejected requirements are left out.")
    print("- Use case complete: Status Tested or Done. Not started: in the diagram without a specification.")
    print("- Code: a file outside docs and tests carries the use case id.")
    print("- Unit: yes when the main scenario, every alternative flow and every business rule is named by a test in a file that carries the use case id; partial when some are.")
    print("- E2E: yes when a journey test case with Status Automated includes the use case; planned when a journey includes it but is not automated yet.")
    print("- Regression: from the test report; unknown without one.")
    print("- Integrity: Strong when Status is Approved or later and Code, Unit and E2E are all yes and nothing regressed; Weak when none of the three has any evidence; Partial otherwise.")
    print("- A marker is a claim. The coverage audit of a use case confirms it by reading.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
