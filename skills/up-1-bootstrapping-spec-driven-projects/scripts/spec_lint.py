#!/usr/bin/env python3
"""Lint a specification set across files, and print the traceability matrix.

Checks what connects the artifacts under a docs folder. Every check is exact
and gives the same result on every run, so this is the part of a review that
may block a build.

ERROR  a specification is not in the diagram; an identifier is used twice; a
       reference points to nothing (a requirement id, a qualified rule citation,
       a use case or process link in a journey test case); a use case file has
       an error of the per-file validator.
WARN   a functional requirement no use case realizes; a requirement Status its
       use cases contradict; the same rule text in two use cases; a word the
       entity model says to avoid; a specification whose name differs from the
       diagram; a citation of a retired rule; a relative link in a specification
       file that leads nowhere; a flow or rule whose name moved to another label
       since the last commit (when the folder is under git); every warning of the
       per-file validator.
INFO   a use case of the diagram without a specification yet; an older file
       spelling; a use case no journey test case includes; a citation into
       another bounded context (billing/UC-003 BR-002); a stale baseline entry;
       a requirements catalog the guideline file expects and that is not written yet.

Output: path:line: SEVERITY CODE [element]: message
Exit code 0 when clean, 1 on any ERROR (with --strict also on any WARN), 2 on usage errors.
--trace always exits 0.

Usage:
    spec_lint.py [--docs DIR] [--only ID] [--strict] [--gate] [--format text|json]
                 [--baseline FILE | --no-baseline] [--update-baseline]
    spec_lint.py --trace [--docs DIR] [--only ID] [--format text|json]

A baseline (default DIR/.spec-lint-baseline.json, written by --update-baseline)
suppresses findings that were accepted when the lint was introduced to an
existing project, so that only new findings fail. Entries are keyed without the
line number and survive edits elsewhere in a file.

Requires Python 3.9+, standard library only. Reads files as data. Writes only
the baseline file, and only with --update-baseline.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model  # noqa: E402  (local module, same folder)
import use_case_map
import validate_use_case  # noqa: E402  (local module, same folder)

# the release these copies belong to; hook_gate.py refuses siblings of another release
UPSPEC_VERSION = "1.2.0"

BASELINE_NAME = ".spec-lint-baseline.json"


def normalize_rule(text):
    """Rule text without its examples, case and punctuation, for spotting copies."""
    text = re.split(r"\bExamples?\s*:", text)[0]
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def moved_labels(uc):
    """Flows and rules whose name sits under another label than in the last commit: [(line, label, name, old label)].

    Labels are identifiers and never move. Nothing is reported outside git or for a file not yet committed."""
    folder, name = os.path.split(os.path.abspath(uc.path))
    code, text = model.git(["show", "HEAD:./" + name], cwd=folder)
    if code != 0:
        return []
    old = model.parse_use_case_lines(text.split("\n"), uc.path)
    key = lambda title: re.sub(r"\s+", " ", title).strip().lower()
    moved = []
    for old_items, new_items in ((old.flows, uc.flows), (old.rules, uc.rules)):
        before = {key(item.name): item.label if hasattr(item, "label") else item.id for item in old_items if item.name and not item.retired}
        for item in new_items:
            label = item.label if hasattr(item, "label") else item.id
            earlier = before.get(key(item.name))
            if item.name and not item.retired and earlier and earlier != label:
                moved.append((item.line, label, item.name, earlier))
    return moved


def derived_status(use_cases):
    """Progress Status a requirement gets from the use cases that link it."""
    ranks = [model.STATUS_RANK[u.status] for u in use_cases if u.status in model.STATUS_RANK]
    if not ranks:
        return None
    implemented, tested = model.STATUS_RANK["Implemented"], model.STATUS_RANK["Tested"]
    if all(r >= tested for r in ranks):
        return "Verified"
    if all(r >= implemented for r in ranks):
        return "Implemented"
    if any(r >= implemented for r in ranks):
        return "In Progress"
    return "Open"


class Project:
    def __init__(self, docs_dir, report):
        self.docs = model.Docs(docs_dir)
        self.report = report
        self.requirements, self.use_cases, self.test_cases = [], [], []
        self.entities = None
        docs = self.docs
        for path, note in docs.notes:
            report.info(path, 0, "SPELLING", "-", note)
        if docs.requirements:
            self.requirements, _ = self._read(docs.requirements, model.parse_requirements, ([], []))
        if docs.entity_model:
            self.entities = self._read(docs.entity_model, model.parse_entity_model, None)
        for path in docs.use_case_files():
            uc = self._read(path, model.parse_use_case, None)
            if uc:
                self.use_cases.append(uc)
        for path in docs.test_case_files():
            tc = self._read(path, model.parse_test_case, None)
            if tc:
                self.test_cases.append(tc)

    def _read(self, path, parser, default):
        try:
            return parser(path)
        except (OSError, UnicodeDecodeError) as exc:
            self.report.error(path, 0, "UNREADABLE", "-", "cannot read the file: %s" % exc)
            return default

    def linking(self):
        """Requirement id -> use cases that link it (Obsolete ones excluded)."""
        result = {}
        for uc in self.use_cases:
            if uc.status == "Obsolete":
                continue
            for rid in uc.requirement_ids:
                result.setdefault(rid, []).append(uc)
        return result


def lint(project):
    report, docs = project.report, project.docs
    nouns = project.entities.nouns() if project.entities else set()

    # per-file checks
    for uc in project.use_cases:
        validate_use_case.check_use_case(uc, report, nouns, bool(docs.requirements))
        for line, label, name, earlier in moved_labels(uc):
            report.warn(uc.path, line, "LABEL_MOVED", "%s %s" % (uc.id, label),
                        "'%s' was %s in the last commit; labels never move: give it %s back, and a new flow or rule the next free number" % (name, earlier, earlier))

    # identifiers
    seen = {}
    for uc in project.use_cases:
        if uc.id and uc.id in seen:
            report.error(uc.path, uc.fields["Use Case ID"][1], "DUPLICATE_ID", uc.id, "identifier is also used by %s" % os.path.basename(seen[uc.id]))
        elif uc.id:
            seen[uc.id] = uc.path
    seen_req = {}
    for req in project.requirements:
        if req.id in seen_req:
            report.error(docs.requirements, req.line, "DUPLICATE_ID", req.id, "identifier is already used on line %d" % seen_req[req.id])
        seen_req.setdefault(req.id, req.line)
    seen_tc = {}
    for tc in project.test_cases:
        if tc.id and tc.id in seen_tc:
            report.error(tc.path, tc.fields["ID"][1], "DUPLICATE_ID", tc.id, "identifier is also used by %s" % os.path.basename(seen_tc[tc.id]))
        elif tc.id:
            seen_tc[tc.id] = tc.path

    by_id = {uc.id: uc for uc in project.use_cases if uc.id}
    for path, line, code, message in model.format_findings(docs):
        report.error(path, line, code, "-", message)
    overview_problem = use_case_map.stale_reason(docs)
    if overview_problem:
        report.error(docs.overview or os.path.join(docs.root, "use_cases.md"), 1,
                     "STALE_OVERVIEW", "-", overview_problem)

    # references
    known_reqs = {r.id for r in project.requirements}
    for uc in project.use_cases:
        if docs.requirements:
            for rid in uc.requirement_ids:
                if rid not in known_reqs:
                    report.error(uc.path, uc.fields["Requirements"][1], "DANGLING_REF", uc.id, "requirement %s is not in the catalog" % rid)
        for line, context, identifier, rule_id, where in uc.external:
            report.info(uc.path, line, "EXTERNAL_REF", "%s %s" % (uc.id, where),
                        "cites %s/%s%s in another bounded context; not checked here" % (context, identifier, " " + rule_id if rule_id else ""))
        for line, other, rule_id, where in uc.citations:
            if not other or other == uc.id:
                continue
            target = by_id.get(other)
            if target is None:
                report.error(uc.path, line, "DANGLING_REF", "%s %s" % (uc.id, where), "cites %s %s, but %s has no specification" % (other, rule_id, other))
            elif rule_id not in [r.id for r in target.rules]:
                report.error(uc.path, line, "DANGLING_REF", "%s %s" % (uc.id, where), "cites %s %s, which %s does not define" % (other, rule_id, other))
            elif rule_id in [r.id for r in target.rules if r.retired]:
                report.warn(uc.path, line, "RULE_RETIRED_CITED", "%s %s" % (uc.id, where), "cites %s %s, which is retired; cite the rule that replaced it" % (other, rule_id))
    used_by_tc = set()
    for tc in project.test_cases:
        element = tc.id or os.path.basename(tc.path)
        if tc.field("Status") and tc.field("Status").split("|")[0].strip() not in model.TC_STATUSES:
            report.error(tc.path, tc.fields["Status"][1], "STATUS_INVALID", element, "Status must be one of %s" % ", ".join(model.TC_STATUSES))
        for uid in tc.use_case_ids():
            used_by_tc.add(uid)
            if uid not in by_id:
                report.error(tc.path, tc.field_line("use_cases"), "DANGLING_REF", element,
                             "journey includes %s, which has no specification" % uid)
        process = tc.field("Process")
        if process and not os.path.exists(os.path.join(os.path.dirname(tc.path), process)):
            report.error(tc.path, tc.field_line("Process"), "DANGLING_REF", element,
                         "process model %s does not exist" % process)
    if project.test_cases:
        for uc in project.use_cases:
            if uc.id and uc.id not in used_by_tc and uc.status != "Obsolete":
                report.info(uc.path, uc.fields.get("Use Case ID", ("", 0))[1], "UC_UNUSED_BY_TC", uc.id, "no journey test case includes this use case")

    # requirement coverage and status
    linking = project.linking()
    if project.requirements and project.use_cases:
        pending = any(uc.is_stub for uc in project.use_cases)
        for req in project.requirements:
            if req.status in model.REQ_SCOPE:
                continue
            ucs = linking.get(req.id, [])
            if req.kind == "FR" and not ucs:
                add = report.info if pending else report.warn
                add(docs.requirements, req.line, "FR_UNREALIZED", req.id, "no use case specification links this requirement")
            wanted = derived_status(ucs)
            if wanted and req.status in model.REQ_PROGRESS and req.status != wanted:
                detail = ", ".join("%s %s" % (u.id, u.status) for u in ucs)
                report.warn(docs.requirements, req.line, "REQ_STATUS_DRIFT", req.id, "Status is '%s' but its use cases make it '%s' (%s)" % (req.status, wanted, detail))

    # copied rules
    texts = {}
    for uc in project.use_cases:
        for rule in uc.rules:
            key = normalize_rule(rule.text())
            if len(key.split()) < 4:      # too short to tell a copy from a coincidence
                continue
            if key in texts and texts[key][0] != uc.id:
                report.warn(uc.path, rule.line, "RULE_COPIED", "%s %s" % (uc.id, rule.id),
                            "same text as %s %s; keep the rule in one use case and cite it" % texts[key])
            texts.setdefault(key, (uc.id, rule.id))

    # links inside the specification files (journey test case links are checked above)
    linked_files = [f for f in [docs.vision, docs.requirements, docs.entity_model] if f] + [u.path for u in project.use_cases]
    if docs.recovery_dir:
        linked_files += sorted(os.path.join(docs.recovery_dir, n) for n in os.listdir(docs.recovery_dir) if n.endswith(".md"))
    for path in linked_files:
        try:
            lines = model.read_lines(path)
        except (OSError, UnicodeDecodeError):
            continue
        for number, target in model.local_links(lines):
            if not os.path.exists(os.path.join(os.path.dirname(path), target)):
                report.warn(path, number, "DEAD_LINK", "-", "link target %s does not exist" % target)

    # a catalog the rules block expects
    root = model.project_root(docs.root)
    guideline, _, skipped = model.read_rules_block(root)
    if guideline and not docs.requirements and "requirements" not in skipped:
        report.info(os.path.join(root, guideline), 0, "CATALOG_PENDING", "-",
                    "the rules block reads use cases against docs/requirements.md, which is not written yet; write it, or record the skip on the **Skipped:** line")

    # avoided words
    if project.entities:
        avoided = [(w, name) for name, e in project.entities.entities.items() for w in e.avoid]
        files = [f for f in [docs.requirements] + [u.path for u in project.use_cases] + [t.path for t in project.test_cases] if f]
        for path in files:
            try:
                lines = model.read_lines(path)
            except (OSError, UnicodeDecodeError):
                continue
            for number, text in model.outside_fences(lines):
                for word, name in avoided:
                    if model.word_hits(text, [word, word + "s"]):
                        report.warn(path, number, "AVOIDED_WORD", name, "'%s' is an avoided word; the entity model's term is %s" % (word, name.replace("_", " ").lower()))


def trace(project):
    """Rows of the two traceability tables."""
    linking = project.linking()
    tcs_of = {}
    for tc in project.test_cases:
        for uc_id in tc.use_case_ids():
            tcs_of.setdefault(uc_id, [])
            if tc.id not in tcs_of[uc_id]:
                tcs_of[uc_id].append(tc.id)
    rows = []
    for req in project.requirements:
        ucs = linking.get(req.id, [])
        wanted = derived_status(ucs)
        status = req.status + (" (use cases: %s)" % wanted if wanted and wanted != req.status and req.status in model.REQ_PROGRESS else "")
        if not ucs:
            rows.append([req.id, req.title or req.need, status, "—", "—", "—"])
        for uc in ucs:
            rows.append([req.id, req.title or req.need, status, "%s %s (%s)" % (uc.id, uc.name, uc.status),
                         ", ".join(r.id for r in uc.rules) or "—", ", ".join(tcs_of.get(uc.id, [])) or "—"])
    for uc in project.use_cases:
        if not uc.requirement_ids:
            rows.append(["—", "—", "—", "%s %s (%s)" % (uc.id, uc.name, uc.status),
                         ", ".join(r.id for r in uc.rules) or "—", ", ".join(tcs_of.get(uc.id, [])) or "—"])
    journeys = [[tc.id or "?", tc.title or "", tc.field("Status"), tc.field("Process") or "—",
                 ", ".join(tc.use_case_ids()) or "—"] for tc in project.test_cases]
    return rows, journeys


def markdown(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def fingerprint(finding):
    return "|".join([finding["code"], finding["path"], finding["element"], finding["message"]])


def main(argv):
    parser = argparse.ArgumentParser(description="Lint a specification set across files.")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--only", help="report only findings about this identifier (UC-001, TC-001, FR-001)")
    parser.add_argument("--gate", action="store_true", help="Draft findings warn without failing, even with --strict")
    parser.add_argument("--strict", action="store_true", help="fail on warnings too")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--trace", action="store_true", help="print the traceability matrix instead of findings")
    parser.add_argument("--baseline", help="baseline file (default: <docs>/%s when it exists)" % BASELINE_NAME)
    parser.add_argument("--no-baseline", action="store_true")
    parser.add_argument("--update-baseline", action="store_true", help="accept all current errors and warnings")
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
    project = Project(args.docs, report)

    if args.trace:
        rows, journeys = trace(project)
        if args.only:
            rows = [r for r in rows if any(args.only in str(c) for c in r)]
            journeys = [j for j in journeys if any(args.only in str(c) for c in j)]
        if args.format == "json":
            print(json.dumps({"requirements": rows, "journeys": journeys}, indent=2, ensure_ascii=False))
        else:
            print(markdown(["Requirement", "Title", "Status", "Use case", "Business rules", "Journey test cases"], rows))
            if journeys:
                print()
                print(markdown(["Journey", "Title", "Status", "Process", "Use cases"], journeys))
        return 0

    lint(project)
    baseline_path = args.baseline or os.path.join(args.docs, BASELINE_NAME)
    if args.update_baseline:
        entries = sorted({fingerprint(f) for f in report.findings if f["severity"] in ("ERROR", "WARN")})
        try:
            with open(baseline_path, "w", encoding="utf-8") as handle:
                json.dump({"accepted": entries}, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
        except OSError as exc:
            print("cannot write the baseline: %s" % exc, file=sys.stderr)
            return 2
        print("%d finding(s) accepted into %s" % (len(entries), baseline_path))
        return 0
    suppressed = 0
    if not args.no_baseline and os.path.isfile(baseline_path):
        try:
            with open(baseline_path, encoding="utf-8") as handle:
                accepted = set(json.load(handle).get("accepted", []))
        except (OSError, ValueError) as exc:
            print("cannot read the baseline %s: %s" % (baseline_path, exc), file=sys.stderr)
            return 2
        current = {fingerprint(f) for f in report.findings}
        kept = [f for f in report.findings if fingerprint(f) not in accepted]
        suppressed = len(report.findings) - len(kept)
        report.findings = kept
        for entry in sorted(accepted - current):
            report.info(baseline_path, 0, "BASELINE_STALE", "-", "accepted finding no longer occurs: %s" % entry.split("|")[0])
    if args.only:
        report.findings = [f for f in report.findings if args.only in f["element"] or args.only in f["path"]]
    draft_findings = set()
    if args.gate:
        drafts = {os.path.relpath(uc.path, report.root).replace(os.sep, "/")
                  for uc in project.use_cases if uc.status == "Draft"}
        for finding in report.findings:
            if finding["path"] in drafts and finding["code"] != "STATUS_INVALID":
                if finding["severity"] == "ERROR":
                    finding["severity"] = "WARN"
                draft_findings.add(id(finding))
    if args.format == "json":
        print(json.dumps({"findings": report.sorted(), "suppressed": suppressed,
                          "summary": {s: report.count(s) for s in ("ERROR", "WARN", "INFO")}}, indent=2, ensure_ascii=False))
    else:
        report.print_text()
        if suppressed:
            print("%d finding(s) suppressed by the baseline" % suppressed)
    return int(any(f["severity"] == "ERROR" or
                   args.strict and f["severity"] == "WARN" and id(f) not in draft_findings
                   for f in report.findings))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
