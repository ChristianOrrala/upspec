#!/usr/bin/env python3
"""Check a requirements catalog row by row.

ERROR  an identifier is malformed or used twice; a functional requirement lacks a
       role or need, or a statement does not follow EARS.
WARN   a non-functional requirement has no number, no verification method or no
       category; a regulatory constraint has no source; a Status is missing or
       unknown; a title or statement is empty; a weak word leaves a decision open.
INFO   a value marked as still to be decided; a need that may hold two
       capabilities; a missing Priority.

Output: path:line: SEVERITY CODE [element]: message
Exit code 0 when clean, 1 on any ERROR (with --strict also on any WARN), 2 on usage errors.

Usage:
    check_requirements.py [--docs DIR] [--strict] [FILE]      (default FILE: docs/requirements.md)

Requires Python 3.9+, standard library only. Reads the file as data; writes nothing.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model  # noqa: E402  (local module, same folder)

UNDECIDED = re.compile(r"<\s*to be decided\s*>", re.IGNORECASE)
# A threshold is a number, or a universal claim a test can falsify with one counterexample.
MEASURABLE = re.compile(r"\d|\b(?:every|each|all|always|never|no|none|only)\b", re.IGNORECASE)
STATUSES = model.REQ_PROGRESS + model.REQ_SCOPE
NFR_CATEGORIES = ("Performance", "Scalability", "Availability", "Security", "Usability", "Maintainability", "Portability")
TEXT_COLUMN = {"FR": "Need", "NFR": "Statement", "C": "Statement"}


def check(path, report):
    requirements, _ = model.parse_requirements(path)
    if not requirements:
        report.error(path, 0, "NO_REQUIREMENTS", "-", "no table row with an FR, NFR or C identifier was found")
        return
    seen = {}
    for req in requirements:
        if not re.fullmatch(r"(?:FR|NFR|C)-\d{3}", req.id):
            report.error(path, req.line, "ID_FORMAT", req.id, "identifiers have three digits, for example %s-001" % req.kind)
        if req.id in seen:
            report.error(path, req.line, "DUPLICATE_ID", req.id, "identifier already used on line %d; never reuse an identifier" % seen[req.id])
        seen.setdefault(req.id, req.line)
        if req.kind != "FR" and not req.title:
            report.warn(path, req.line, "EMPTY_CELL", req.id, "Title is empty")
        if not req.text:
            report.warn(path, req.line, "EMPTY_CELL", req.id, "%s is empty" % TEXT_COLUMN[req.kind])
        undecided = bool(UNDECIDED.search(" ".join(req.row.values())))
        if undecided:
            report.info(path, req.line, "UNDECIDED", req.id, "a value is still to be decided; it needs an open entry in the conflict ledger")

        if req.kind == "FR" and re.search(r"\b(?:and|as well as)\b", req.need, re.IGNORECASE):
            report.info(path, req.line, "COMPOUND", req.id, "the need contains 'and'; if these are two capabilities, split the row")
        if req.kind == "NFR":
            if req.text and not MEASURABLE.search(req.text) and not undecided:
                report.warn(path, req.line, "NFR_NOT_MEASURABLE", req.id, "state a threshold with a number, or mark it <to be decided> and open a ledger entry")
            if "Verification" not in req.row:
                report.warn(path, req.line, "NFR_NO_VERIFICATION", req.id, "the table has no Verification column; say how the threshold will be checked")
            elif not req.row["Verification"]:
                report.warn(path, req.line, "NFR_NO_VERIFICATION", req.id, "Verification is empty; say how the threshold will be checked")
            category = req.row.get("Category", "")
            if category and category not in NFR_CATEGORIES:
                report.warn(path, req.line, "CATEGORY_UNKNOWN", req.id, "Category '%s' is not one of %s" % (category, ", ".join(NFR_CATEGORIES)))
        if req.kind == "C" and req.row.get("Category", "").lower() == "regulatory":
            source = req.row.get("Source", "")
            if not source or UNDECIDED.search(source):
                report.warn(path, req.line, "CONSTRAINT_NO_SOURCE", req.id, "a regulatory constraint names its source down to the article or section")

        if not req.status:
            report.warn(path, req.line, "STATUS_EMPTY", req.id, "Status is empty; a new row starts as Open")
        elif req.status not in STATUSES:
            report.warn(path, req.line, "STATUS_UNKNOWN", req.id, "Status '%s' is not one of %s" % (req.status, ", ".join(STATUSES)))
        if not req.priority:
            report.info(path, req.line, "PRIORITY_EMPTY", req.id, "Priority is empty")
        for word in model.word_hits(req.text, model.WEAK_WORDS):
            report.warn(path, req.line, "WEAK_WORD", req.id, "'%s' leaves a decision open; state the decision or open a ledger entry" % word)


def main(argv):
    parser = argparse.ArgumentParser(description="Check a requirements catalog.")
    parser.add_argument("file", nargs="?", default=None)
    parser.add_argument("--docs", help="the specification folder (default: the positional file's folder, else the recorded folder)")
    parser.add_argument("--strict", action="store_true", help="fail on warnings too")
    args = parser.parse_args(argv)
    docs_dir = args.docs or (os.path.dirname(os.path.abspath(args.file)) if args.file else model.docs_default())
    args.file = args.file or os.path.join(docs_dir, "requirements.md")
    docs = model.Docs(docs_dir)
    report = model.Reporter(os.getcwd())
    stop = model.stop_if_old(docs)
    if stop is not None:
        return stop
    if not os.path.isfile(args.file):
        print("no such file: %s" % args.file, file=sys.stderr)
        return 2
    if docs.requirements != args.file:
        docs.requirements = args.file
        stop = model.stop_if_old(docs)
        if stop is not None:
            return stop
    try:
        for path, line, code, message in model.format_findings(docs, kinds=("requirements",)):
            report.error(path, line, code, "-", message)
        check(args.file, report)
    except (OSError, UnicodeDecodeError) as exc:
        report.error(args.file, 0, "UNREADABLE", "-", "cannot read the file: %s" % exc)
    report.print_text()
    return report.exit_code(args.strict)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
