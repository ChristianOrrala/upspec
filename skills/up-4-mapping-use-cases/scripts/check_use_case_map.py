#!/usr/bin/env python3
"""Check the use case diagram against its conventions, the specifications and the catalog.

ERROR  the diagram has no @startuml or @enduml; a use case identifier is malformed
       or declared twice; a specification file's use case is not in the diagram.
WARN   a label without identifier and name on two lines; no system rectangle; an
       actor or a use case connected to nothing; a specification whose name
       differs from the diagram; a functional requirement no use case realizes.
INFO   a use case of the diagram without a specification yet; a name that looks
       like a subfunction or an aggregate; no specification links requirements yet.

Output: path:line: SEVERITY CODE [element]: message
Exit code 0 when clean, 1 on any ERROR (with --strict also on any WARN), 2 on usage errors.

Usage:
    check_use_case_map.py [--docs DIR] [--strict]      (default DIR: docs)

Requires Python 3.9+, standard library only. Reads files as data; writes nothing.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model  # noqa: E402  (local module, same folder)

# First words that usually name a step of a larger goal, not a goal an actor comes for.
SUBFUNCTION_VERBS = ("validate", "check", "load", "fetch", "persist", "save", "store", "process", "handle",
                     "calculate", "parse", "convert", "retrieve", "look", "search", "find")


def check(docs, report):
    path = docs.diagram
    diagram = model.parse_diagram(path)
    if not (diagram.has_start and diagram.has_end):
        report.error(path, 0, "NO_START_END", "-", "the diagram needs @startuml and @enduml")
    if not diagram.system:
        report.warn(path, 0, "NO_SYSTEM", "-", "put the use cases in a rectangle that carries the system's real name")
    for line, label in diagram.bad_labels:
        report.warn(path, line, "LABEL_FORM", "-", "label '%s' must be the identifier and the name on two lines: \"UC-001\\nVerb Object\"" % label)
    for line, uc_id in diagram.duplicates:
        report.error(path, line, "DUPLICATE_ID", uc_id, "identifier is declared twice")
    linked = set()
    for line, left, right, _ in diagram.links:
        linked.update((left, right))
    for alias, (name, line) in sorted(diagram.actors.items()):
        if alias not in linked:
            report.warn(path, line, "ACTOR_UNCONNECTED", name, "actor is connected to no use case")
    for uc_id, (name, alias, line) in sorted(diagram.use_cases.items()):
        if not re.fullmatch(r"UC-\d{3}", uc_id):
            report.error(path, line, "ID_FORMAT", uc_id, "identifiers are UC- and three digits")
        actor_link = any((left == alias and right in diagram.actors) or (right == alias and left in diagram.actors)
                         for _, left, right, _ in diagram.links)
        if not actor_link:
            report.warn(path, line, "USE_CASE_UNCONNECTED", uc_id, "use case is connected to no actor")
        first = name.split()[0].lower() if name.split() else ""
        if first in SUBFUNCTION_VERBS:
            report.info(path, line, "SUBFUNCTION_NAME", uc_id, "'%s' reads like a step of a larger goal; ask why the actor does it" % name)
        if first == "manage":
            report.info(path, line, "AGGREGATE", uc_id, "'%s' is an aggregate; split out any operation with its own actor, preconditions or rules" % name)

    # specifications against the diagram
    specs = {}
    for file in docs.use_case_files():
        try:
            uc = model.parse_use_case(file)
        except (OSError, UnicodeDecodeError) as exc:
            report.error(file, 0, "UNREADABLE", "-", "cannot read the file: %s" % exc)
            continue
        if not uc.id:
            continue
        specs[uc.id] = uc
        if uc.id not in diagram.use_cases:
            if uc.status != "Obsolete":
                report.error(file, uc.fields.get("Use Case ID", ("", 0))[1], "SPEC_NOT_IN_DIAGRAM", uc.id, "specification exists but the use case is not in the diagram")
        elif uc.name and uc.name != diagram.use_cases[uc.id][0]:
            report.warn(file, uc.fields.get("Use Case Name", ("", 0))[1], "NAME_MISMATCH", uc.id,
                        "specification says '%s', the diagram says '%s'" % (uc.name, diagram.use_cases[uc.id][0]))
    for uc_id, (name, alias, line) in sorted(diagram.use_cases.items()):
        if uc_id not in specs:
            report.info(path, line, "SPEC_PENDING", uc_id, "'%s' has no specification yet" % name)

    # requirements coverage
    if docs.requirements:
        requirements, _ = model.parse_requirements(docs.requirements)
        realized = set()
        for uc in specs.values():
            if uc.status != "Obsolete":
                realized.update(uc.requirement_ids)
        if specs and not realized:
            report.info(path, 0, "NO_TRACEABILITY", "-", "no specification has a Requirements line yet, so coverage cannot be checked")
        elif specs:
            pending = any(uc_id not in specs for uc_id in diagram.use_cases)
            for req in requirements:
                if req.kind == "FR" and req.status not in model.REQ_SCOPE and req.id not in realized:
                    message = "no use case specification links this requirement"
                    if pending:
                        report.info(docs.requirements, req.line, "FR_UNREALIZED", req.id, message + " (some use cases have no specification yet)")
                    else:
                        report.warn(docs.requirements, req.line, "FR_UNREALIZED", req.id, message)


def main(argv):
    parser = argparse.ArgumentParser(description="Check the use case diagram.")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--strict", action="store_true", help="fail on warnings too")
    args = parser.parse_args(argv)
    args.docs = args.docs or model.docs_default()
    if not os.path.isdir(args.docs):
        print("no such folder: %s" % args.docs, file=sys.stderr)
        return 2
    docs = model.Docs(args.docs)
    if not docs.diagram:
        print("no use case diagram in %s (expected use_cases.puml)" % args.docs, file=sys.stderr)
        return 2
    report = model.Reporter(os.getcwd())
    try:
        check(docs, report)
    except (OSError, UnicodeDecodeError) as exc:
        report.error(docs.diagram, 0, "UNREADABLE", "-", "cannot read the file: %s" % exc)
    report.print_text()
    return report.exit_code(args.strict)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
