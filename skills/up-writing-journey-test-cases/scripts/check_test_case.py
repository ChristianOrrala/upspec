#!/usr/bin/env python3
"""Check journey test case documents.

ERROR  a missing Overview field or Flow section; an identifier or Status
       outside the convention; wrong Flow columns; a use case link or process
       link that points to nothing; a linked use case without a specification.
WARN   steps not numbered from 1; no verification row; placeholder test data;
       mechanism vocabulary; fewer than two use cases (not a journey); missing
       roles, validation or postconditions; an invalid Priority; a file name
       that does not carry the identifier.
INFO   a precondition without its data source; a linked use case still in Draft.

Output: path:line: SEVERITY CODE [element]: message
Exit code 0 when clean, 1 on any ERROR (with --strict also on any WARN), 2 on usage errors.

Usage:
    check_test_case.py [--docs DIR] [--strict] FILE...

--docs defaults to the parent of the folder holding the first file.

Requires Python 3.9+, standard library only. Reads files as data; writes nothing.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model  # noqa: E402  (local module, same folder)

COLUMNS = ["Step", "Name", "Description", "Test Data", "Use Case"]
PRIORITIES = ("Critical", "High", "Medium", "Low")
PLACEHOLDER = re.compile(r"\b(?:a|an|any|some)\s+(?:valid|existing|random|arbitrary|sample|test)\b|\be\.g\.|\bfor example\b|\blorem\b|\bfoo\b|\bxxx\b|<[^>]+>", re.IGNORECASE)
SELECTOR = re.compile(r"(?:^|\s)[#.][a-z][\w-]*\b(?=\s|$)|\bxpath\b|\bselector\b|\bcss\b|\bdata-testid\b", re.IGNORECASE)


def check(path, docs, report):
    tc = model.parse_test_case(path)
    element = tc.id or os.path.basename(path)
    for label in ("ID", "Goal", "Status"):
        if not tc.field(label):
            report.error(path, tc.section_lines.get("Overview", 0), "FIELD_MISSING", element, "Overview has no **%s:** value" % label)
    if tc.field("ID") and not re.fullmatch(r"TC-\d{3}", tc.field("ID").strip()):
        report.error(path, tc.fields["ID"][1], "ID_FORMAT", element, "identifier must be TC- and three digits")
    status = tc.field("Status").split("|")[0].strip()
    if tc.field("Status") and status not in model.TC_STATUSES:
        report.error(path, tc.fields["Status"][1], "STATUS_INVALID", element, "Status must be one of %s" % ", ".join(model.TC_STATUSES))
    priority = tc.field("Priority").split("|")[0].strip()
    if priority not in PRIORITIES:
        report.warn(path, tc.fields.get("Priority", ("", tc.section_lines.get("Overview", 0)))[1], "PRIORITY_INVALID", element, "Priority must be one of %s" % ", ".join(PRIORITIES))
    name = os.path.basename(path)
    if tc.id and not re.fullmatch(re.escape(tc.id) + r"-[a-z0-9]+(?:-[a-z0-9]+)*\.md", name):
        report.warn(path, 0, "FILE_NAME", element, "file should be named %s-<kebab-case-goal>.md" % tc.id)
    if "Flow" not in tc.section_lines or not tc.flow_header:
        report.error(path, 0, "SECTION_MISSING", element, "no '## Flow' table")
        return
    if tc.flow_header != COLUMNS:
        report.error(path, tc.section_lines["Flow"], "FLOW_COLUMNS", element, "Flow columns must be: %s" % " | ".join(COLUMNS))
        return
    numbers = [row.get("Step", "") for _, row in tc.flow_rows]
    if numbers != [str(i) for i in range(1, len(numbers) + 1)]:
        report.warn(path, tc.section_lines["Flow"], "STEP_NUMBERING", element, "steps must be numbered from 1 without gaps, got %s" % ", ".join(numbers))
    by_id = {}
    if docs:
        for file in docs.use_case_files():
            match = model.RE_UC_ID.search(os.path.basename(file))
            if match:
                by_id[match.group(0)] = file
    linked, verification = [], 0
    for line, row in tc.flow_rows:
        cell, data = row.get("Use Case", ""), row.get("Test Data", "")
        row_element = "%s step %s" % (element, row.get("Step", "?"))
        match = model.RE_UC_ID.search(cell)
        if not match:
            verification += 1
        else:
            uc_id = match.group(0)
            linked.append(uc_id)
            link = re.search(r"\]\(([^)]+)\)", cell)
            if not link:
                report.warn(path, line, "NO_LINK", row_element, "link the use case specification: [%s](../use_cases/%s-<name>.md)" % (uc_id, uc_id))
            elif not os.path.exists(os.path.join(os.path.dirname(path), link.group(1))):
                report.error(path, line, "DANGLING_REF", row_element, "link target %s does not exist" % link.group(1))
            if docs and uc_id not in by_id:
                report.error(path, line, "DANGLING_REF", row_element, "%s has no specification; a journey must not chain a use case that is not specified" % uc_id)
            elif docs:
                try:
                    if model.parse_use_case(by_id[uc_id]).status == "Draft":
                        report.info(path, line, "DRAFT_USE_CASE", row_element, "%s is still Draft; the journey rests on text that may change" % uc_id)
                except (OSError, UnicodeDecodeError):
                    pass
        for text in (data, row.get("Description", "")):
            if PLACEHOLDER.search(text):
                report.warn(path, line, "PLACEHOLDER_DATA", row_element, "use literal values; a placeholder cannot be automated")
            if SELECTOR.search(text) or model.pattern_hits(text, model.MECHANISM_TERMS):
                report.warn(path, line, "MECHANISM_TERM", row_element, "describe the step in business language, without selectors or other mechanism")
        if not row.get("Name"):
            report.warn(path, line, "EMPTY_CELL", row_element, "Name is empty")
    if len(set(linked)) < 2:
        report.warn(path, tc.section_lines["Flow"], "SINGLE_USE_CASE", element, "a journey chains at least two use cases; the tests of one use case belong to that use case")
    if not verification:
        report.warn(path, tc.section_lines["Flow"], "NO_VERIFICATION", element, "add a verification row (a '-' in the Use Case column) after an action the next step depends on")
    if not tc.roles:
        report.warn(path, tc.section_lines.get("Roles", 0), "ROLES_EMPTY", element, "list every role that acts in the flow")
    if not tc.validations:
        report.warn(path, tc.section_lines.get("Validation", 0), "NO_VALIDATION", element, "add at least one numbered end-state check")
    if not tc.postconditions:
        report.warn(path, tc.section_lines.get("Postconditions", 0), "NO_POSTCONDITIONS", element, "list every record the journey creates or changes")
    for line, text in tc.preconditions:
        if PLACEHOLDER.search(text):
            report.warn(path, line, "PLACEHOLDER_DATA", element, "preconditions name literal data")
        elif "(" not in text:
            report.info(path, line, "PRECONDITION_SOURCE", element, "say where this data is seeded from, in parentheses")
    process = re.search(r"\]\(([^)]+)\)", tc.field("Process"))
    if process and not os.path.exists(os.path.join(os.path.dirname(path), process.group(1))):
        report.error(path, tc.fields["Process"][1], "DANGLING_REF", element, "process model %s does not exist" % process.group(1))


def main(argv):
    parser = argparse.ArgumentParser(description="Check journey test case documents.")
    parser.add_argument("files", nargs="+")
    parser.add_argument("--docs", help="docs folder (default: parent of the first file's folder)")
    parser.add_argument("--strict", action="store_true", help="fail on warnings too")
    args = parser.parse_args(argv)
    docs_dir = args.docs or os.path.dirname(os.path.dirname(os.path.abspath(args.files[0])))
    docs = model.Docs(docs_dir) if os.path.isdir(docs_dir) else None
    report = model.Reporter(os.getcwd())
    for path in args.files:
        if not os.path.isfile(path):
            print("no such file: %s" % path, file=sys.stderr)
            return 2
        try:
            check(path, docs, report)
        except (OSError, UnicodeDecodeError) as exc:
            report.error(path, 0, "UNREADABLE", "-", "cannot read the file: %s" % exc)
    report.print_text()
    return report.exit_code(args.strict)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
