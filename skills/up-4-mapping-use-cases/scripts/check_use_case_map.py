#!/usr/bin/env python3
"""Check the use case files, generated overview and requirement coverage.

Exit 0 clean, 1 findings, 2 usage, 5 old formats. Python 3.9+, standard library only.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import use_case_map
import spec_model as model  # noqa: E402  (local module, same folder)

# First words that usually name a step of a larger goal, not a goal an actor comes for.
SUBFUNCTION_VERBS = ("validate", "check", "load", "fetch", "persist", "save", "store", "process", "handle",
                     "calculate", "parse", "convert", "retrieve", "look", "search", "find")


def check(docs, report):
    for path, line, code, message in model.format_findings(docs, kinds=("use_case",)):
        report.error(path, line, code, "-", message)
    overview_problem = use_case_map.stale_reason(docs)
    if overview_problem:
        report.error(docs.overview or os.path.join(docs.root, "use_cases.md"), 1,
                     "STALE_OVERVIEW", "-", overview_problem)
    specs = model.load_use_cases(docs)
    seen = set()
    for uc in specs:
        if uc.field("Use Case ID") and not re.fullmatch(r"UC-\d{3}", uc.field("Use Case ID")):
            report.error(uc.path, uc.field_line("Use Case ID"), "ID_FORMAT", uc.id, "identifiers are UC- and three digits")
        if uc.id in seen:
            report.error(uc.path, uc.field_line("Use Case ID"), "DUPLICATE_ID", uc.id, "identifier is declared twice")
        if uc.id:
            seen.add(uc.id)
        first = uc.name.split()[0].lower() if uc.name.split() else ""
        if first in SUBFUNCTION_VERBS:
            report.info(uc.path, uc.field_line("Use Case Name"), "SUBFUNCTION_NAME", uc.id, "'%s' reads like a step of a larger goal; ask why the actor does it" % uc.name)
        if first == "manage":
            report.info(uc.path, uc.field_line("Use Case Name"), "AGGREGATE", uc.id, "'%s' is an aggregate; split out operations with their own actor, preconditions or rules" % uc.name)
    if docs.requirements:
        requirements, _ = model.parse_requirements(docs.requirements)
        realized = {rid for uc in specs if uc.status != "Obsolete" for rid in uc.requirement_ids}
        if specs and not realized:
            report.info(docs.overview or docs.root, 0, "NO_TRACEABILITY", "-", "no use case links requirements yet, so coverage cannot be checked")
        elif specs:
            for req in requirements:
                if req.kind == "FR" and req.status not in model.REQ_SCOPE and req.id not in realized:
                    report.warn(docs.requirements, req.line, "FR_UNREALIZED", req.id, "no use case links this requirement")


def main(argv):
    parser = argparse.ArgumentParser(description="Check the use case overview.")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--strict", action="store_true", help="fail on warnings too")
    args = parser.parse_args(argv)
    args.docs = args.docs or model.docs_default()
    if not os.path.isdir(args.docs):
        print("no such folder: %s" % args.docs, file=sys.stderr)
        return 2
    docs = model.Docs(args.docs)
    stop = model.stop_if_old(docs)
    if stop:
        return stop
    report = model.Reporter(os.getcwd())
    try:
        check(docs, report)
    except (OSError, UnicodeDecodeError) as exc:
        report.error(docs.overview or docs.root, 0, "UNREADABLE", "-", "cannot read the file: %s" % exc)
    report.print_text()
    return report.exit_code(args.strict)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
