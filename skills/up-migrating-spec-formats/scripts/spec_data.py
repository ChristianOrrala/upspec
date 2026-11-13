#!/usr/bin/env python3
"""Print the whole model of a specification-driven project as JSON, for a program to read.

Everything the shared parser reads, in one document with stable keys: the rules block; every use case with its
front matter, goal, trigger, actors, preconditions, steps, flows, rules, postconditions, citations and references
into other bounded contexts; the requirements; the entities and their relations; the journeys; the change records;
the recovery ledger and change log; the review reports; the A-files. Each element carries its file, its line and a
fingerprint. A kind of file the project lacks keeps its key, empty, with present false, so that an absent file and
an empty one can be told apart: a folder that exists and holds nothing is present with no items. Nothing is judged
here: the checks say what is wrong.

Fingerprints are the first 16 hex digits of a SHA-256. A file's is of its bytes. A rule's, a flow's, a step's, a
precondition's and a postcondition's is of the text the guard check fingerprints for that element, so it can be
compared with the guard-check log. A table row's is of the row as written, its white space normalized; any other
element's is of its text, its white space normalized.

Exit code 0 when the model was printed; 1 when a file or a folder could not be read (the model is printed without
it, and it is listed under unreadable; every A-file and guideline file that exists is read for this); 2 on usage
errors; 3 when it could not run: the parser beside it (spec_model.py) is of another release, as when an older copy
was kept in tools/specs/ (run scaffold_docs.py --update); 5 when the project still uses upspec's earlier formats
(OLD_FORMAT on standard error, nothing printed: migrate first).

Setup installs a copy into the project's tools/specs/ with the other installed scripts (either set), and its
update keeps it current, so that a program can run the project's own copy.

Usage:
    spec_data.py [--docs DIR] [--format json]

Requires Python 3.9+, standard library only. Reads files as data; writes nothing, not even a bytecode cache.
"""
import argparse
import copy
import glob
import json
import os
import re
import sys

sys.dont_write_bytecode = True   # a __pycache__ folder beside an installed copy would be a file this command wrote
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model  # noqa: E402  (local module, same folder)

# the release this copy belongs to; the state reader's update notice and setup's update read it
UPSPEC_VERSION = "1.8.0"

# The shape of the output. It changes only when a key changes its meaning or goes away; a new key keeps it.
SCHEMA = 1
# The artifacts the skipped line of the rules block can name, as the state reader lists them.
SKIPPABLE = ("requirements", "entity model", "overview", "diagram")
# What read_tracking() gives, empty, for a project without the A-files.
EMPTY_TRACKING = {"current_work": "", "blocked_by": "", "waiting_on_owner": "", "debt": [], "abilities": {},
                  "next_up": [], "items": {}, "item_titles": {}, "abilities_present": False, "active_home": None,
                  "abilities_home": None, "ahead_home": None, "next_step": "", "next_new_work": "", "ahead_items": {}}
TRACKING_FILES = ("AGENTS.md", "CLAUDE.md", "ACTIVE.md", "ABILITIES.md", "AHEAD.md", "ATLAS.md")


class Reader:
    """Reads the project's files for one run: paths relative to the root, fingerprints, and the files it could not
    read."""

    def __init__(self, root):
        self.root = root
        self.unreadable = []

    def rel(self, path):
        return os.path.relpath(path, self.root).replace(os.sep, "/") if path else None

    def attempt(self, path, function, *args):
        """function(*args), or None when the file cannot be read; the file is then listed as unreadable."""
        try:
            return function(*args)
        except (OSError, UnicodeDecodeError) as exc:
            entry = {"file": self.rel(getattr(exc, "spec_path", None) or path), "error": str(exc)}
            if entry not in self.unreadable:
                self.unreadable.append(entry)
            return None

    def lines(self, path):
        return self.attempt(path, model.read_lines, path) or []

    def listing(self, folder, function=None):
        """function() for a folder that exists, after making sure it can be listed; [] when it cannot be, the folder
        then listed as unreadable, or when there is no folder."""
        if not folder:
            return []
        if self.attempt(folder, os.listdir, folder) is None:
            return []
        return (self.attempt(folder, function) if function else []) or []

    def fingerprint(self, path):
        """The fingerprint of a file's bytes, or None when it cannot be read."""
        def read(name):
            with open(name, "rb") as handle:
                return model.fingerprint(handle.read())
        return self.attempt(path, read, path)


def text_print(text):
    return model.fingerprint(model.norm_text(text or ""))


def at(file, line, text=None, fingerprint=None):
    """Where an element is: its file, its line and its fingerprint (of the text given, else the one given)."""
    return {"file": file, "line": line, "fingerprint": fingerprint if fingerprint is not None else text_print(text)}


def row_print(lines, line):
    """The fingerprint of a table row as written."""
    return text_print(lines[line - 1] if 0 < line <= len(lines) else "")


def front_matter_data(fm):
    return {"values": {key: {"value": value, "line": line} for key, (value, line) in fm.meta.items()},
            "problems": [{"line": line, "message": message} for line, message in fm.problems],
            "refused": dict(fm.refused)}


# --- use cases ----------------------------------------------------------------

def numbered_items(file, items, prefix):
    return [dict({"name": "%s%d" % (prefix, number), "number": number, "text": text}, **at(file, line, text))
            for number, (line, text) in enumerate(items, 1)]


def step_data(file, step, flow=None):
    """A step: in the main scenario named 'Step 3', in a flow 'A1 step 2'."""
    name = "%s step %d" % (flow, step.number) if flow else "Step %d" % step.number
    return dict({"name": name, "number": step.number, "text": step.text}, **at(file, step.line, step.text))


def field_element(uc, file, label):
    """A front matter value as an element ({text, file, line, fingerprint}), or None when the key is absent."""
    key = model.FIELD_KEYS[label]
    if key not in uc.meta:
        return None
    return dict({"text": uc.field(label)}, **at(file, uc.field_line(label), uc.field(label)))


def flow_data(file, flow):
    ending = None
    if flow.ending:
        ending = {"kind": flow.ending[0], "step": flow.ending[1], "line": flow.ending_line}
    trigger = dict({"text": flow.trigger, "steps": flow.trigger_steps,
                    "flow_steps": [{"flow": label, "step": number} for label, number in flow.trigger_flow_steps],
                    "any_time": flow.any_time}, **at(file, flow.trigger_line, flow.trigger))
    return dict({"label": flow.label, "name": flow.name, "trigger": trigger,
                 "steps": [step_data(file, step, flow.label) for step in flow.steps], "ending": ending,
                 "retired": flow.retired, "moved_to": flow.moved_to},
                **at(file, flow.line, fingerprint=model.fingerprint(model.flow_text(flow))))


def rule_data(file, rule):
    examples = None
    if rule.examples:
        examples = {"line": rule.examples["line"], "header": rule.examples["header"],
                    "rows": [{"line": line, "cells": cells} for line, cells in rule.examples["rows"]]}
    return dict({"id": rule.id, "name": rule.name, "text": rule.text(), "examples": examples,
                 "retired": rule.retired, "moved_to": rule.moved_to},
                **at(file, rule.line, fingerprint=model.fingerprint(model.rule_text(rule))))


def use_case_data(reader, uc):
    file = reader.rel(uc.path)
    actors = []
    for role, key, names in (("primary", "primary_actor", uc.primary_actors),
                             ("secondary", "secondary_actors", uc.secondary_actors)):
        line = uc.meta.get(key, ("", 0))[1]
        actors += [dict({"name": name, "role": role}, **at(file, line, name)) for name in names]
    requirements_line = uc.field_line("Requirements")
    citations = [dict({"use_case": cited, "rule": rule, "where": where,
                       "target": "%s %s" % (cited or uc.id, rule) if cited or uc.id else rule},
                      **at(file, line, "%s %s" % (cited, rule) if cited else rule))
                 for line, cited, rule, where in uc.citations]
    references = [dict({"context": context, "id": identifier, "rule": rule, "where": where},
                       **at(file, line, "%s/%s%s" % (context, identifier, " " + rule if rule else "")))
                  for line, context, identifier, rule, where in uc.external]
    return {
        "id": uc.id, "file": file, "fingerprint": reader.fingerprint(uc.path), "line_count": uc.line_count,
        "name": uc.name, "status": uc.status, "stub": uc.is_stub,
        "title": {"text": uc.title, "line": uc.title_line} if uc.title is not None else None,
        "front_matter": front_matter_data(uc.front_matter),
        "goal": field_element(uc, file, "Goal"), "trigger": field_element(uc, file, "Trigger"),
        "actors": actors,
        "requirements": [dict({"id": rid}, **at(file, requirements_line, rid)) for rid in uc.requirement_ids],
        "sections": {name: {"title": uc.section_titles[name], "line": line} for name, line in uc.section_lines.items()},
        "duplicate_sections": [{"name": name, "title": title, "line": line} for name, title, line in uc.duplicate_sections],
        "preconditions": numbered_items(file, uc.preconditions, "Pre-"),
        "steps": [step_data(file, step) for step in uc.steps],
        "flows": [flow_data(file, flow) for flow in uc.flows],
        "flows_placeholder": {"text": uc.flows_placeholder[1], "line": uc.flows_placeholder[0]} if uc.flows_placeholder else None,
        "postconditions": {"success": numbered_items(file, uc.success, "Post-S-"),
                           "failure": numbered_items(file, uc.failure, "Post-F-")},
        "rules": [rule_data(file, rule) for rule in uc.rules],
        "citations": citations,
        "references": references,
    }


# --- the other artifacts --------------------------------------------------------

def requirements_data(reader, docs):
    section = {"present": bool(docs and docs.requirements), "file": reader.rel(docs and docs.requirements),
               "fingerprint": None, "items": []}
    if not section["present"]:
        return section
    section["fingerprint"] = reader.fingerprint(docs.requirements)
    lines = reader.lines(docs.requirements)
    parsed = reader.attempt(docs.requirements, model.parse_requirements, docs.requirements)
    for req in (parsed[0] if parsed else []):
        section["items"].append(dict({
            "id": req.id, "kind": req.kind, "title": model.requirement_title(req), "text": req.text,
            "role": req.role, "need": req.need, "statement": req.statement, "status": req.status,
            "priority": req.priority, "columns": dict(req.row)},
            **at(section["file"], req.line, fingerprint=row_print(lines, req.line))))
    return section


def entities_data(reader, docs):
    section = {"present": bool(docs and docs.entity_model), "file": reader.rel(docs and docs.entity_model),
               "fingerprint": None, "diagram": {"present": False, "entities": []}, "items": [], "relations": [],
               "duplicates": []}
    if not section["present"]:
        return section
    file = section["file"]
    section["fingerprint"] = reader.fingerprint(docs.entity_model)
    lines = reader.lines(docs.entity_model)
    parsed = reader.attempt(docs.entity_model, model.parse_entity_model, docs.entity_model)
    if parsed is None:
        return section
    bodies = {line: "\n".join([title] + [text for _, text in body]) for title, line, body in model.sections(lines, 3)}
    section["diagram"] = {"present": parsed.has_diagram,
                          "entities": [{"name": name, "line": line} for name, line in parsed.diagram_entities.items()]}
    for entity in parsed.entities.values():
        attributes = []
        for line, row, _ in entity.attributes:
            reference = model.RE_REFERENCE.fullmatch(row.get("Type", "").strip())
            attributes.append(dict({"name": row.get("Attribute", ""), "meaning": row.get("Meaning", ""),
                                    "type": row.get("Type", ""), "rules": row.get("Rules", ""),
                                    "reference": reference.group(1) if reference else None, "columns": dict(row)},
                                   **at(file, line, fingerprint=row_print(lines, line))))
        section["items"].append(dict({
            "name": entity.name, "description": entity.description, "avoid": entity.avoid,
            "attributes": attributes,
            "lifecycle": {"text": entity.lifecycle[1], "line": entity.lifecycle[0]} if entity.lifecycle else None,
            "constraints": [{"text": text, "line": line} for line, text in entity.constraints]},
            **at(file, entity.line, bodies.get(entity.line, entity.name))))
    section["relations"] = [dict({"from": left, "to": right, "label": label}, **at(file, line, fingerprint=row_print(lines, line)))
                            for line, left, right, label in parsed.relationships]
    section["duplicates"] = [{"name": name, "line": line} for line, name in parsed.duplicates]
    return section


def journeys_data(reader, docs):
    folder = docs.test_case_dir if docs else None
    section = {"present": bool(folder), "folder": reader.rel(folder), "items": []}
    for path in reader.listing(folder, docs and docs.test_case_files):
        tc = reader.attempt(path, model.parse_test_case, path)
        if tc is None:
            continue
        file = reader.rel(path)
        scenarios = []
        for scenario in tc.scenarios:
            flows = {}
            for line, uc_id, flow in scenario.named_flows:
                flows.setdefault(line, []).append({"use_case": uc_id, "flow": flow})
            scenarios.append({
                "name": scenario.name, "line": scenario.line,
                "steps": [dict({"keyword": keyword, "text": text, "use_cases": list(ids), "flows": flows.get(line, [])},
                               **at(file, line, "%s %s" % (keyword, text)))
                          for line, keyword, text, ids in scenario.steps],
                "problems": [{"line": line, "message": message} for line, message in scenario.problems]})
        section["items"].append({
            "id": tc.id, "file": file, "fingerprint": reader.fingerprint(path), "title": tc.title,
            "front_matter": front_matter_data(tc.front_matter),
            "goal": tc.field("goal"), "priority": tc.field("Priority"), "status": tc.field("status").strip(),
            "process": tc.field("Process"), "use_cases": tc.use_case_ids(),
            "roles": [{"text": text, "line": line} for line, text in tc.roles],
            "preconditions": [{"text": text, "line": line} for line, text in tc.preconditions],
            "postconditions": [{"text": text, "line": line} for line, text in tc.postconditions],
            "scenarios": scenarios,
            "problems": [{"line": line, "message": message} for line, message in tc.gherkin_problems]})
    return section


def differences(lines):
    """The rows of a change record's table with an Element and a Today column: [{line, element, units, columns}]."""
    for table in model.read_tables(lines):
        header = [cell.strip().lower() for cell in table["header"]]
        if "element" not in header or not any(cell.startswith("today") for cell in header):
            continue
        column = table["header"][header.index("element")]
        return [{"line": line, "element": row.get(column, "").strip(),
                 "use_cases": model.RE_UC_ID.findall(row.get(column, "")),
                 "units": model.UNIT.findall(row.get(column, "")), "columns": dict(row)}
                for line, row, _ in table["rows"] if row.get(column, "").strip()]
    return []


def change_record_folders(docs):
    """Every change-records folder under the specification folder, an empty one included."""
    found = glob.glob(os.path.join(glob.escape(docs.root), "**", "change-records"), recursive=True) if docs else []
    return sorted(path for path in found if os.path.isdir(path))


def change_records_data(reader, docs):
    folders = change_record_folders(docs)
    section = {"present": bool(folders), "folders": [reader.rel(folder) for folder in folders], "items": []}
    for folder in folders:
        reader.listing(folder)           # a folder that cannot be listed is recorded; its records cannot be read
    for path in (docs.change_record_files() if docs else []):
        record = reader.attempt(path, model.parse_change_record, path)
        if record is None:
            continue
        section["items"].append({
            "file": reader.rel(path), "fingerprint": reader.fingerprint(path),
            "front_matter": front_matter_data(record.front_matter), "outcome": record.outcome,
            "element": record.element, "use_cases": model.RE_UC_ID.findall(record.element),
            "decided_by": model._as_text(record.meta.get("decided_by", ("", 0))[0]) or None,
            "sections": dict(record.sections), "differences": differences(reader.lines(path))})
    return section


def recovery_data(reader, docs):
    folder = docs.recovery_dir if docs else None
    section = {"present": bool(folder), "folder": reader.rel(folder)}
    reader.listing(folder)
    for key, name, parse, items in (("ledger", "ledger.md", model.parse_ledger, "rows"),
                                    ("change_log", "change-log.md", model.parse_change_log, "entries")):
        path = os.path.join(folder, name) if folder else None
        present = bool(path and os.path.isfile(path))
        part = {"present": present, "file": reader.rel(path) if present else None,
                "fingerprint": reader.fingerprint(path) if present else None, items: []}
        if present:
            lines = reader.lines(path)
            file = part["file"]
            part[items] = [dict(row, **at(file, row["line"], fingerprint=row_print(lines, row["line"])))
                           for row in (reader.attempt(path, parse, path) or [])]
        section[key] = part
    return section


def reviews_data(reader, docs):
    folder = docs.reviews_dir if docs else None
    section = {"present": bool(folder), "folder": reader.rel(folder), "items": []}
    for path in reader.listing(folder, docs and docs.review_files):
        report = reader.attempt(path, model.read_review_report, path)
        if report is not None:
            section["items"].append(dict(report, file=reader.rel(path), fingerprint=reader.fingerprint(path)))
    return section


def tracking_data(reader, root):
    # The parser reads the A-files and the guideline file leniently, as optional; each one that exists is read here
    # too, so that one that cannot be read or decoded is listed under unreadable instead of reading as empty.
    files = {}
    for name in TRACKING_FILES:
        path = os.path.join(root, name)
        present = os.path.isfile(path)
        readable = present and reader.attempt(path, model.read_lines, path) is not None
        files[name] = {"present": present, "readable": readable,
                       "fingerprint": reader.fingerprint(path) if present else None}
    present = model.a_files_present(root)
    tracking = reader.attempt(os.path.join(root, "ACTIVE.md"), model.read_tracking, root) if present else None
    return dict({"present": present, "files": files}, **(tracking or copy.deepcopy(EMPTY_TRACKING)))


def rules_block_data(root):
    name, profile, skipped = model.read_rules_block(root)
    return {"present": name is not None, "file": name, "profile": profile,
            "skipped": [word for word in SKIPPABLE if word in skipped], "skipped_text": skipped,
            "specs_folder": model.recorded_docs(root), "integration_branch": model.integration_branch(root)}


def collect(docs_dir):
    """The model of the project whose specification folder is docs_dir: (data, unreadable files)."""
    root = model.project_root(docs_dir)
    reader = Reader(root)
    docs = model.Docs(docs_dir) if os.path.isdir(docs_dir) else None
    reader.listing(docs and docs_dir)
    use_cases = []
    for path in reader.listing(docs and docs.use_case_dir, docs and docs.use_case_files):
        uc = reader.attempt(path, model.parse_use_case, path)
        if uc is not None:
            use_cases.append(use_case_data(reader, uc))
    files = {}
    for kind, attribute in (("vision", "vision"), ("requirements", "requirements"), ("entity_model", "entity_model"),
                            ("overview", "overview"), ("use_cases", "use_case_dir"), ("journeys", "test_case_dir"),
                            ("processes", "process_dir"), ("recovery", "recovery_dir"), ("reviews", "reviews_dir")):
        path = getattr(docs, attribute) if docs else None
        files[kind] = {"present": bool(path), "path": reader.rel(path)}
    data = {
        "schema": SCHEMA, "upspec_version": model.UPSPEC_VERSION,
        "root": os.path.abspath(root), "docs": reader.rel(os.path.abspath(docs_dir)), "docs_present": docs is not None,
        "files": files,
        "rules_block": rules_block_data(root),
        "use_cases": {"present": bool(docs and docs.use_case_dir), "folder": reader.rel(docs and docs.use_case_dir),
                      "items": use_cases},
        "requirements": requirements_data(reader, docs),
        "entities": entities_data(reader, docs),
        "journeys": journeys_data(reader, docs),
        "change_records": change_records_data(reader, docs),
        "recovery": recovery_data(reader, docs),
        "reviews": reviews_data(reader, docs),
        "tracking": tracking_data(reader, root),
    }
    data["unreadable"] = reader.unreadable
    return data


def main(argv):
    parser = argparse.ArgumentParser(description="Print the whole model of a specification-driven project as JSON.")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--format", choices=("json",), default="json", help="the output format; JSON is the only one")
    args = parser.parse_args(argv)
    found = getattr(model, "UPSPEC_VERSION", None)
    if found != UPSPEC_VERSION:
        # A copy kept from an older release beside this one lacks what this command reads: say so instead of failing.
        print("spec_model.py beside spec_data.py is %s, and spec_data.py is %s: the copies come from different "
              "releases. Run scaffold_docs.py --update to bring tools/specs/ to one release."
              % ("release " + found if found else "of a release before 1.1.0", UPSPEC_VERSION), file=sys.stderr)
        return 3
    args.docs = args.docs or model.docs_default()
    if os.path.exists(args.docs) and not os.path.isdir(args.docs):
        print("not a folder: %s" % args.docs, file=sys.stderr)
        return 2
    if os.path.isdir(args.docs):
        try:
            earlier = model.old_formats(model.Docs(args.docs))
        except (OSError, UnicodeDecodeError):
            earlier = []          # the unreadable file is listed under unreadable below
        if earlier:
            for path, line, what in earlier:
                sys.stderr.write("%s:%d: ERROR OLD_FORMAT: %s\n" % (path, line, what))
            sys.stderr.write("This project uses upspec's earlier formats. Migrate it first: the skill "
                             "up-migrating-spec-formats (scripts/migrate_formats.py plan).\n")
            return model.OLD_FORMAT_EXIT
    data = collect(args.docs)
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 1 if data["unreadable"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
