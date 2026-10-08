#!/usr/bin/env python3
"""Check the recovery records against the recovered specifications and the code.

The records live in DIR/recovery/: the ledger (ledger.md), the suspect list
(suspects.md), the change log (change-log.md), the baseline review plan
(baseline-review.md) and change records (change-records/*.md). Only the ledger
is required.

ERROR  a ledger row with an unknown State; an evidence location whose file does
       not exist; a dropped change log entry without its reason; an entry in
       change whose change record does not exist; an aligned entry whose audit
       report does not exist, or whose reports between them do not name every
       use case of the entry.
WARN   a claim not built (kind Claimed but not built) without the old document's
       line; an entry in change with no use case, or whose record's file name
       names none; an aligned entry whose report still shows a gap;
       a recovered use case, flow or rule without a ledger row; a row naming a
       flow or rule the specification does not have; a row without evidence; an
       evidence line beyond the end of its file; a suspect or discarded row
       without a note; a suspect row that names no entry of the suspect list; a
       suspect element whose specification text does not name its suspect id; an
       entity with an identifier, required attributes or a lifecycle and no row
       citing where the schema or the code says so (ENTITY NAME required, which
       covers the identifier and its type, ENTITY NAME lifecycle);
       a citation in any record that resolves to nothing; a Status written into
       a record instead of being read from the use case; a suspect with an
       unknown kind, a repeated id, or the same evidence as another suspect.
INFO   an entity of the model without a ledger row; a use case of the diagram
       without a ledger row.

States: recovered (the code does this and it reads as intended), verified (a
second reader checked the claim against its evidence), suspect, discarded.

The change log is also the alignment backlog. Decision later (or later: <the
decision>) is open work; in change: <change record path> means a change took
it up; aligned: <audit report>[; <audit report>] closes it, written by whoever
acts on the audit; dropped: <reason> closes it without work.

After the findings it prints the counts of the recovery (use cases, Status,
ledger rows, suspects, change log entries). Quote these counts; do not write
counts or Status values into the records by hand, they go stale.

Output: path:line: SEVERITY CODE [element]: message
Exit code 0 when clean, 1 on any ERROR (with --strict also on any WARN), 2 on usage errors.

Usage:
    check_recovery_ledger.py [--docs DIR] [--ledger FILE] [--root DIR] [--strict]

--ledger defaults to DIR/recovery/ledger.md. --root is the folder evidence
paths are relative to (default: the current folder). Evidence is path:line or
path:first-last, several separated by semicolons.

Requires Python 3.9+, standard library only. Reads files as data; writes nothing.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model  # noqa: E402  (local module, same folder)

STATES = ("recovered", "verified", "suspect", "discarded")
# The identifier counts as required: its type is the entity fact a recovery guessed most
# in the third real-project trial (sequence numbers where the schema had generated values).
REQUIRED = re.compile(r"\b(?:primary key|not null|required)\b", re.IGNORECASE)
KINDS = ("decide", "tidy")
ELEMENT = re.compile(r"^(UC-\d{3})(?:\s+(A\d+|BR-\d{3}))?$")
CITATION = re.compile(r"(?<![\w/-])(UC-\d{3})(?:\s+(A\d+|BR-\d{3}))?\b")
SUSPECT_ID = re.compile(r"\bS-\d{2,3}\b")
# "UC-003 is Draft", "specified as Draft", "Status: Reviewed": a Status copied into a record.
STATUS_CLAIM = re.compile(r"\b(?:Status:?|is|are|as|stays|remains|marked|now)\s+[*`]{0,2}(Draft|Reviewed|Approved|Implemented|Tested|Done)\b")
RECORDS = ("suspects.md", "change-log.md", "baseline-review.md")
# Words that fill the Decision column of a change log while nothing is decided yet (shared with the router).
UNDECIDED = model.RE_UNDECIDED


def line_count(path):
    try:
        with open(path, "rb") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return 0


def table_rows(lines, first_column):
    """Rows of every table whose first header cell is first_column (case-insensitive): [(line, row dict)]."""
    rows = []
    for table in model.read_tables(lines):
        if table["header"] and table["header"][0].strip().lower() == first_column:
            rows += [(line, row) for line, row, _ in table["rows"]]
    return rows


def check_evidence(report, path, line, element, cell, root):
    """Evidence is path:line locations separated by semicolons. Returns the normalized locations."""
    evidence = [e.strip().strip("`") for e in cell.split(";") if e.strip()]
    for item in evidence:
        match = re.fullmatch(r"(.+?):(\d+)(?:-(\d+))?", item)      # path:line or path:first-last
        target, number = (match.group(1), int(match.group(3) or match.group(2))) if match else (item, None)
        full = os.path.join(root, target)
        if not os.path.isfile(full):
            report.error(path, line, "EVIDENCE_MISSING", element, "%s does not exist under %s" % (target, root))
        elif number is None:
            report.warn(path, line, "EVIDENCE_LINE", element, "%s has no line number; write path:line" % target)
        elif number > line_count(full):
            report.warn(path, line, "EVIDENCE_LINE", element, "%s has fewer than %d lines" % (target, number))
    return evidence


class Known:
    """What citations may resolve to: use case files with their flows and rules."""

    def __init__(self, specs):
        self.specs = {uc.id: uc for uc in specs if uc.id}

    def problem(self, uc_id, part):
        uc = self.specs.get(uc_id)
        if uc is None:
            return "%s has no use case file" % uc_id
        if uc.is_stub and part:
            return "%s is a stub, so %s %s cannot be cited yet" % (uc_id, uc_id, part)
        if part and part.startswith("BR-") and part not in [r.id for r in uc.rules]:
            return "%s does not define %s" % (uc_id, part)
        if part and part.startswith("A") and part not in [f.label for f in uc.flows]:
            return "%s has no flow %s" % (uc_id, part)
        return None


def element_text(known, element):
    """Text of a specified element (the whole file for a use case), or None when it is not specified."""
    match = ELEMENT.match(element)
    uc = known.specs.get(match.group(1)) if match else None
    if uc is None:
        return None
    part = match.group(2)
    if not part:
        return "\n".join(model.read_lines(uc.path))
    for flow in uc.flows:
        if flow.label == part:
            return "\n".join([flow.name, flow.trigger] + [s.text for s in flow.steps])
    for rule in uc.rules:
        if rule.id == part:
            return rule.name + "\n" + rule.text()
    return None


def check_citations(report, path, number, text, known, element="-"):
    for match in CITATION.finditer(text):
        problem = known.problem(match.group(1), match.group(2))
        if problem:
            cited = match.group(1) + (" " + match.group(2) if match.group(2) else "")
            report.warn(path, number, "CITATION_UNKNOWN", element, "cites %s: %s" % (cited, problem))


def check_status_claims(report, path, lines):
    for number, text in model.outside_fences(lines):
        match = STATUS_CLAIM.search(text)
        if match and (model.RE_UC_ID.search(text) or re.search(r"\bspecifications?\b", text, re.IGNORECASE)):
            report.warn(path, number, "STATUS_RESTATED", "-",
                        "'%s' copies a Status into a record; the Status line of the use case is its only home, so refer to it" % match.group(0).strip())


def check_suspects(report, path, root):
    """Returns the suspect ids and (decide, tidy) counts."""
    lines = model.read_lines(path)
    rows = table_rows(lines, "id")
    if not rows:
        report.warn(path, 0, "SUSPECTS_FORMAT", "-", "no table with the columns Id | Kind | Use case | What the system does | Evidence | Question")
        return set(), (0, 0)
    ids, seen_evidence, counts = {}, {}, {"decide": 0, "tidy": 0}
    for line, row in rows:
        sid = row.get("Id", "").strip()
        if not sid or sid.startswith("["):
            continue
        if sid in ids:
            report.warn(path, line, "SUSPECT_DUPLICATE", sid, "the id is also used on line %d" % ids[sid])
            continue
        ids[sid] = line
        kind = row.get("Kind", "").strip().lower()
        if kind not in KINDS:
            report.warn(path, line, "KIND_INVALID", sid, "Kind must be decide (the owner settles it in the baseline review) or tidy (no behavior question)")
        else:
            counts[kind] += 1
        evidence = tuple(sorted(check_evidence(report, path, line, sid, row.get("Evidence", ""), root)))
        key = (row.get("Use case", "").strip(), evidence)
        if evidence and key in seen_evidence:
            report.warn(path, line, "SUSPECT_DUPLICATE", sid, "same use case and evidence as %s; keep one entry" % seen_evidence[key])
        seen_evidence.setdefault(key, sid)
    return set(ids), (counts["decide"], counts["tidy"])


def check_backlog_entry(report, path, entry, root):
    """The alignment backlog's rules for one change log entry."""
    element, line, state = "#%d" % entry["number"], entry["line"], entry["state"]
    if state == "dropped" and not entry["detail"]:
        report.error(path, line, "REASON_MISSING", element, "a dropped entry keeps its reason: dropped: <why>")
    if state == "in_change":
        record = entry["paths"][0] if entry["paths"] else ""
        if not os.path.isfile(os.path.join(root, record)):
            report.error(path, line, "CHANGE_RECORD_MISSING", element,
                         "%s does not exist under %s; in change names the change record's path" % (record or "the record", root))
        if not entry["use_cases"]:
            report.warn(path, line, "USE_CASE_MISSING", element, "write the use case the change creates or changes into the Use case column")
        named = model.RE_UC_ID.search(os.path.basename(record)) if record else None
        if named and named.group(0) not in entry["use_cases"]:
            report.warn(path, line, "USE_CASE_MISSING", element,
                        "write the change record's use case %s into the Use case column" % named.group(0))
        if record and not named:
            report.warn(path, line, "RECORD_UNNAMED", element, "a change record is named after its use case: docs/change-records/UC-XXX-<name>.md")
    for severity, code, message in model.closure_problems(root, entry):
        emit = report.error if severity == "error" else report.warn
        emit(path, line, code, element, message)
    if model.RE_CLAIM_KIND.match(entry["kind"]):
        if not check_evidence(report, path, line, element, entry["evidence"], root):
            report.warn(path, line, "EVIDENCE_EMPTY", element, "a claim not built cites the old document's line, path:line")


def check(docs, ledger_path, root, report):
    """Returns the counts for the summary, or None when the ledger has no table."""
    lines = model.read_lines(ledger_path)
    rows = table_rows(lines, "element")
    if not rows:
        report.error(ledger_path, 0, "LEDGER_EMPTY", "-", "no table with the columns Element | Evidence | State | Note")
        return None
    specs = model.load_use_cases(docs)
    known = Known(specs)
    record_dir = os.path.dirname(ledger_path)
    suspects_path = os.path.join(record_dir, "suspects.md")
    suspect_ids, suspect_counts = (check_suspects(report, suspects_path, root) if os.path.isfile(suspects_path) else (None, (0, 0)))

    seen, states = set(), {state: 0 for state in STATES}
    for line, row in rows:
        element = row.get("Element", "").strip().strip("`")
        if not element or element.startswith("["):
            continue
        seen.add(element)
        state = row.get("State", "").strip().lower()
        note = row.get("Note", "").strip()
        if state not in STATES:
            report.error(ledger_path, line, "STATE_INVALID", element, "State must be one of %s" % ", ".join(STATES))
        else:
            states[state] += 1
            if state in ("suspect", "discarded") and not note:
                report.warn(ledger_path, line, "NOTE_MISSING", element, "a %s row says why in the Note column" % state)
        text = element_text(known, element) if state == "suspect" else None
        if text is not None:
            unmarked = [sid for sid in SUSPECT_ID.findall(note) if sid not in text]
            if unmarked:
                report.warn(ledger_path, line, "SUSPECT_NOT_MARKED", element,
                            "the specification does not name %s where this element is written; add it in the text, for example (%s)" % (", ".join(unmarked), unmarked[0]))
        if state == "suspect" and suspect_ids is not None:
            named = SUSPECT_ID.findall(note)
            if not named or not all(sid in suspect_ids for sid in named):
                report.warn(ledger_path, line, "SUSPECT_UNLISTED", element, "a suspect row names its entry in suspects.md (for example S-012), and the entry exists")
        if not check_evidence(report, ledger_path, line, element, row.get("Evidence", ""), root):
            report.warn(ledger_path, line, "EVIDENCE_EMPTY", element, "no code location given")
        check_citations(report, ledger_path, line, note, known, element)

    present = set()
    for uc in specs:
        if not uc.id:
            continue
        wanted = [uc.id] + ["%s %s" % (uc.id, f.label) for f in uc.flows if not f.retired] + ["%s %s" % (uc.id, r.id) for r in uc.rules if not r.retired]
        present.update([uc.id] + ["%s %s" % (uc.id, f.label) for f in uc.flows] + ["%s %s" % (uc.id, r.id) for r in uc.rules])
        for element in wanted:
            if element not in seen:
                report.warn(uc.path, 0, "LEDGER_MISSING", element, "recovered element has no ledger row")
    spec_ids = {uc.id for uc in specs if uc.id}
    for line, row in rows:
        element = row.get("Element", "").strip().strip("`")
        match = ELEMENT.match(element)
        if match and match.group(2) and match.group(1) in spec_ids and element not in present:
            report.warn(ledger_path, line, "LEDGER_STALE", element, "the specification of %s has no such flow or rule" % match.group(1))
    if docs.entity_model:
        for name, entity in model.parse_entity_model(docs.entity_model).entities.items():
            if "ENTITY %s" % name not in seen:
                report.info(docs.entity_model, entity.line, "LEDGER_MISSING", "ENTITY %s" % name, "entity has no ledger row naming where it was recovered from")
            required = [row.get("Attribute", "?") for _, row, _ in entity.attributes if row.get("Type", "") == "Identifier" or REQUIRED.search(row.get("Rules", ""))]
            if required and "ENTITY %s required" % name not in seen:
                report.warn(docs.entity_model, entity.line, "LEDGER_MISSING", "ENTITY %s required" % name,
                            "%s marked identifier or required; add a row citing the schema line of each, which also shows its type (a guess here is the commonest recovery error)" % ", ".join(required))
            if entity.lifecycle and "ENTITY %s lifecycle" % name not in seen:
                report.warn(docs.entity_model, entity.lifecycle[0], "LEDGER_MISSING", "ENTITY %s lifecycle" % name,
                            "the lifecycle needs a row citing where the code writes each state; a state nothing writes is a suspect")

    open_entries = entries = 0
    backlog = {"later": 0, "in_change": 0, "aligned": 0, "dropped": 0}
    change_dir = os.path.join(record_dir, "change-records")
    extra = sorted(os.path.join("change-records", n) for n in os.listdir(change_dir) if n.endswith(".md")) if os.path.isdir(change_dir) else []
    for name in list(RECORDS) + extra:
        path = os.path.join(record_dir, name)
        if not os.path.isfile(path):
            continue
        record = model.read_lines(path)
        check_status_claims(report, path, record)
        for number, text in model.outside_fences(record):
            check_citations(report, path, number, text, known)
        if name == "change-log.md":
            for entry in model.parse_change_log(path):
                entries += 1
                # Decided means someone decided: options written into the Decision column are not a decision.
                decided_by = entry["decided_by"]
                open_entries += bool(entry["state"] == "undecided"
                                     or (decided_by is not None and UNDECIDED.match(decided_by.strip().strip("*_"))))
                if entry["state"] in backlog:
                    backlog[entry["state"]] += 1
                check_backlog_entry(report, path, entry, root)

    statuses = {}
    for uc in specs:
        statuses[uc.status] = statuses.get(uc.status, 0) + 1
    return {"map": len(spec_ids), "specified": len(spec_ids), "statuses": statuses,
            "rows": sum(states.values()), "states": states, "suspects": suspect_counts if suspect_ids is not None else None,
            "entries": entries, "open": open_entries, "backlog": backlog}


def print_summary(counts):
    print("Recovery: %d use cases on the map, %d specified (%s)" % (
        counts["map"], counts["specified"], ", ".join("%s %d" % (s, n) for s, n in sorted(counts["statuses"].items())) or "none"))
    print("Ledger: %d rows (%s)" % (counts["rows"], ", ".join("%s %d" % (s, n) for s, n in counts["states"].items())))
    if counts["suspects"] is not None:
        print("Suspects: %d to decide, %d to tidy" % counts["suspects"])
    print("Change log: %d entries, %d without a decision" % (counts["entries"], counts["open"]))
    if any(counts["backlog"].values()):
        print("Backlog: %(later)d later, %(in_change)d in change, %(aligned)d aligned, %(dropped)d dropped" % counts["backlog"])


def main(argv):
    parser = argparse.ArgumentParser(description="Check the recovery records.")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--ledger")
    parser.add_argument("--root", default=".")
    parser.add_argument("--strict", action="store_true", help="fail on warnings too")
    args = parser.parse_args(argv)
    args.docs = args.docs or model.docs_default()
    docs_model = model.Docs(args.docs)
    stop = model.stop_if_old(docs_model)
    if stop:
        return stop
    if not os.path.isdir(args.docs) or not os.path.isdir(args.root):
        print("no such folder: %s" % (args.docs if not os.path.isdir(args.docs) else args.root), file=sys.stderr)
        return 2
    ledger = args.ledger or os.path.join(args.docs, "recovery", "ledger.md")
    if not os.path.isfile(ledger):
        print("no ledger at %s" % ledger, file=sys.stderr)
        return 2
    report = model.Reporter(os.getcwd())
    counts = None
    try:
        counts = check(model.Docs(args.docs), ledger, args.root, report)
    except (OSError, UnicodeDecodeError) as exc:
        report.error(ledger, 0, "UNREADABLE", "-", "cannot read: %s" % exc)
    report.print_text()
    if counts:
        print_summary(counts)
    return report.exit_code(args.strict)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
