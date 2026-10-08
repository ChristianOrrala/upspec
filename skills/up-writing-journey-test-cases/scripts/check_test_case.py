#!/usr/bin/env python3
"""Check journey front matter, Gherkin, use case and process references,
literal data, business language, roles and postconditions.

Output: path:line: SEVERITY CODE [element]: message
Exit code 0 when clean, 1 on ERROR (with --strict also on WARN), 2 on usage errors,
5 for earlier formats. Python 3.9+, standard library only; reads only.
Usage: check_test_case.py [--docs DIR] [--strict] FILE...
--docs defaults to the parent of the first file's folder.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model  # noqa: E402  (local module, same folder)

PRIORITIES = ("Critical", "High", "Medium", "Low")
PLACEHOLDER = re.compile(r"\b(?:a|an|any|some)\s+(?:valid|existing|random|arbitrary|sample|test)\b|\be\.g\.|\bfor example\b|\blorem\b|\bfoo\b|\bxxx\b|<[^>]+>", re.IGNORECASE)
SELECTOR = re.compile(r"(?:^|\s)[#.][a-z][\w-]*\b(?=\s|$)|\bxpath\b|\bselector\b|\bcss\b|\bdata-testid\b", re.IGNORECASE)


def check(path, docs, report):
    tc = model.parse_test_case(path)
    element = tc.id or os.path.basename(path)
    if tc.field("ID") and not re.fullmatch(r"TC-\d{3}", tc.field("ID").strip()):
        report.error(path, tc.field_line("ID"), "ID_FORMAT", element, "identifier must be TC- and three digits")
    status = tc.field("Status").strip()
    if tc.field("Status") and status not in model.TC_STATUSES:
        report.error(path, tc.field_line("Status"), "STATUS_INVALID", element, "Status must be one of %s" % ", ".join(model.TC_STATUSES))
    priority = tc.field("Priority").strip()
    if priority not in PRIORITIES:
        report.warn(path, tc.field_line("Priority"), "PRIORITY_INVALID", element, "Priority must be one of %s" % ", ".join(PRIORITIES))
    name = os.path.basename(path)
    if tc.id and not re.fullmatch(re.escape(tc.id) + r"-[a-z0-9]+(?:-[a-z0-9]+)*\.md", name):
        report.warn(path, 0, "FILE_NAME", element, "file should be named %s-<kebab-case-goal>.md" % tc.id)
    by_id = {model.parse_use_case(file).id: file for file in docs.use_case_files()}
    linked = tc.use_case_ids()
    for uc_id in linked:
        if uc_id not in by_id:
            report.error(path, tc.field_line("use_cases"), "DANGLING_REF", element, "use case %s has no specification" % uc_id)
        else:
            uc = model.parse_use_case(by_id[uc_id])
            if uc.status == "Draft":
                report.info(path, tc.field_line("use_cases"), "DRAFT_USE_CASE", element, "%s is still Draft" % uc_id)
    verification = 0
    for scenario in tc.scenarios:
        for line, keyword, text, _ in scenario.steps:
            if keyword == "Then":
                verification += 1
            if PLACEHOLDER.search(text):
                report.warn(path, line, "PLACEHOLDER_DATA", element, "use literal values; a placeholder cannot be automated")
            if SELECTOR.search(text) or model.pattern_hits(text, model.MECHANISM_TERMS):
                report.warn(path, line, "MECHANISM_TERM", element, "describe the step in business language, without selectors or other mechanism")
    if len(set(linked)) < 2:
        report.warn(path, tc.field_line("use_cases"), "SINGLE_USE_CASE", element, "a journey chains at least two use cases; the tests of one use case belong to that use case")
    if not verification:
        report.warn(path, 0, "NO_VERIFICATION", element, "add Then steps to verify the action's result and the closing state")
    if not tc.roles:
        report.warn(path, tc.section_lines.get("Roles", 0), "ROLES_EMPTY", element, "list every role that acts in the flow")
    if not tc.postconditions:
        report.warn(path, tc.section_lines.get("Postconditions", 0), "NO_POSTCONDITIONS", element, "list every record the journey creates or changes")
    for line, text in tc.preconditions:
        if PLACEHOLDER.search(text):
            report.warn(path, line, "PLACEHOLDER_DATA", element, "preconditions name literal data")
        elif "(" not in text:
            report.info(path, line, "PRECONDITION_SOURCE", element, "say where this data is seeded from, in parentheses")
    process = tc.field("Process")
    if process and not os.path.exists(os.path.join(os.path.dirname(path), process)):
        report.error(path, tc.field_line("Process"), "DANGLING_REF", element, "process model %s does not exist" % process)


def main(argv):
    parser = argparse.ArgumentParser(description="Check journey test case documents.")
    parser.add_argument("files", nargs="+")
    parser.add_argument("--docs", help="docs folder (default: parent of the first file's folder)")
    parser.add_argument("--strict", action="store_true", help="fail on warnings too")
    args = parser.parse_args(argv)
    docs_dir = args.docs or os.path.dirname(os.path.dirname(os.path.abspath(args.files[0])))
    if not os.path.isdir(docs_dir):
        print("no such folder: %s" % docs_dir, file=sys.stderr)
        return 2
    docs = model.Docs(docs_dir)
    report = model.Reporter(os.getcwd())
    for path in args.files:
        if not os.path.isfile(path):
            print("no such file: %s" % path, file=sys.stderr)
            return 2
    # Inspect the supplied journeys, including files outside the conventional folder.
    journeys = sorted(set(docs.test_case_files() + args.files))
    docs.test_case_files = lambda: journeys
    stop = model.stop_if_old(docs)
    if stop is not None:
        return stop
    docs.test_case_files = lambda: args.files
    try:
        for path, line, code, message in model.format_findings(docs, kinds=("journey",)):
            report.error(path, line, code, "-", message)
    except (OSError, UnicodeDecodeError) as exc:
        report.error(docs.root, 0, "UNREADABLE", "-", "cannot read journeys: %s" % exc)
    for path in args.files:
        try:
            check(path, docs, report)
        except (OSError, UnicodeDecodeError) as exc:
            report.error(path, 0, "UNREADABLE", "-", "cannot read the file: %s" % exc)
    report.print_text()
    return report.exit_code(args.strict)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
