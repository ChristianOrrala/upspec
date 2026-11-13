#!/usr/bin/env python3
"""List what refers to an identifier or a business noun, so a change's reach is known before it is made.

Terms can be:
  a requirement id        FR-001, NFR-002, C-001
  a use case id           UC-002
  a qualified rule        "UC-002 BR-001"
  a journey id            TC-001
  a business noun         "work order"

For each term the script prints three groups:
  upward    what it rests on: requirements a use case links, the entity that defines a noun
  sideways  other specifications that cite or use it
  downward  journey test cases, and code and test files that carry the identifier

With --format json, each term also gives its kind (term_kind: requirement,
rule, use_case, journey, noun) and, beside each group's sentences, the same
items typed, one for one and in the same order (upward_items, sideways_items,
downward_items). A typed item holds the sentence (text) and:
  kind   catalog_row, rule, entity, attribute, missing, links, cites,
         includes, marks, mentions
  from   the end that refers: a use case with the flow or rule where the
         line sits in one (UC-004 A1), a journey, a requirement, a code
         location (path:line), or the term itself
  to     the end referred to (UC-002 BR-001, FR-001, WORK_ORDER.status), or
         null when nothing was found
  basis  what the connection rests on: catalog, specification, entity_model,
         requirements_line, citation, journey, marker (an identifier in a code
         or test file: a claim), text (a line's text matches)
  file, line  where it was found, or null

Exit code 0, 1 when a file cannot be read, 2 on usage errors, 5 on earlier
specification formats.

Usage:
    impact.py TERM [TERM ...] [--docs DIR] [--code DIR] [--format text|json]

--code is the folder searched for identifiers in code and tests (default: the
current folder). The docs folder itself is never searched as code.

Requires Python 3.9+, standard library only. Reads files as data; writes nothing.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model  # noqa: E402  (local module, same folder)

FLOW_OR_RULE = re.compile(r"A\d+|BR-\d{3}")


def part_at(uc, line):
    """The flow or rule of a use case a line sits in (A1, BR-002), or None in any other section."""
    section = None
    for start, name in sorted((start, name) for name, start in uc.section_lines.items()):
        if start <= line:
            section = name
    items = {"Alternative Flows": [(f.line, f.label) for f in uc.flows],
             "Business Rules": [(r.line, r.id) for r in uc.rules]}.get(section, [])
    found = None
    for start, label in sorted(items):
        if start <= line:
            found = label
    return found if found and FLOW_OR_RULE.fullmatch(found) else None


class Index:
    def __init__(self, docs_dir, code_dir):
        self.docs = model.Docs(docs_dir)
        self.code_dir = code_dir
        self.docs_abs = os.path.abspath(docs_dir)
        self.requirements = []
        if self.docs.requirements:
            self.requirements, _ = model.parse_requirements(self.docs.requirements)
        self.use_cases = model.load_use_cases(self.docs)
        self.test_cases = [model.parse_test_case(p) for p in self.docs.test_case_files()]
        self.entities = model.parse_entity_model(self.docs.entity_model) if self.docs.entity_model else None

    def rel(self, path):
        return os.path.relpath(path)

    def code_hits(self, uc_id, extra=None):
        """Lines in code and tests that carry the identifier: [(path, line, text)]."""
        hits = []
        for path, line, text in model.find_markers(self.code_dir, uc_id):
            if os.path.abspath(path).startswith(self.docs_abs + os.sep):
                continue
            if extra is None or extra.search(text):
                hits.append((path, line, text))
        return hits

    def journeys_with(self, uc_id):
        return [tc for tc in self.test_cases if uc_id in tc.use_case_ids()]

    def text_mentions(self, pattern, skip=None):
        """Lines in specifications that match the pattern: [(path, line, text)]."""
        found = []
        files = [f for f in [self.docs.requirements] if f] + [u.path for u in self.use_cases] + [t.path for t in self.test_cases]
        for path in files:
            if skip and os.path.abspath(path) == os.path.abspath(skip):
                continue
            try:
                lines = model.read_lines(path)
            except (OSError, UnicodeDecodeError):
                continue
            for number, text in model.outside_fences(lines):
                if pattern.search(text):
                    found.append((path, number, text))
        return found

    def element_at(self, path, line):
        """The address of what a specification line belongs to: a use case with its flow or rule (UC-004 A1), a
        journey, a requirement's row; else the file."""
        where = os.path.abspath(path)
        for uc in self.use_cases:
            if os.path.abspath(uc.path) == where and uc.id:
                part = part_at(uc, line)
                return "%s %s" % (uc.id, part) if part else uc.id
        for tc in self.test_cases:
            if os.path.abspath(tc.path) == where and tc.id:
                return tc.id
        if self.docs.requirements and os.path.abspath(self.docs.requirements) == where:
            for req in self.requirements:
                if req.line == line:
                    return req.id
        return self.rel(path)


def impact_of(term, index):
    result = {"term": term, "upward": [], "sideways": [], "downward": []}
    typed = {"upward": [], "sideways": [], "downward": []}

    def add(group, text, kind, start, end, basis, path=None, line=None):
        result[group].append(text)
        typed[group].append({"text": text, "kind": kind, "from": start, "to": end, "basis": basis,
                             "file": index.rel(path) if path else None, "line": line or None})

    def journeys(uc_id):
        for tc in index.journeys_with(uc_id):
            add("downward", "%s %s (%s)" % (tc.id, tc.title, tc.field("Status")), "includes", tc.id, uc_id, "journey",
                tc.path, tc.field_line("use_cases"))

    def markers(target, identifier, extra=None):
        for path, line, text in index.code_hits(identifier, extra):
            where = "%s:%d" % (index.rel(path), line)
            add("downward", "%s  %s" % (where, text.strip()[:100]), "marks", where, target, "marker", path, line)

    by_id = {u.id: u for u in index.use_cases if u.id}
    qualified = re.fullmatch(r"(UC-\d{3})\s+(BR-\d{3})", term)
    if re.fullmatch(r"(?:FR|NFR|C)-\d{3}", term):
        kind = "requirement"
        req = next((r for r in index.requirements if r.id == term), None)
        if req:
            add("upward", "%s %s (Status %s)" % (term, req.title, req.status), "catalog_row", term, term, "catalog",
                index.docs.requirements, req.line)
        else:
            add("upward", "%s is not in the catalog" % term, "missing", term, None, "catalog")
        for uc in index.use_cases:
            if term in uc.requirement_ids:
                add("sideways", "%s %s (Status %s) links it" % (uc.id, uc.name, uc.status), "links", uc.id, term,
                    "requirements_line", uc.path, uc.field_line("Requirements"))
                journeys(uc.id)
    elif qualified:
        kind = "rule"
        uc_id, rule_id = qualified.groups()
        target = "%s %s" % (uc_id, rule_id)
        uc = by_id.get(uc_id)
        rule = next((r for r in uc.rules if r.id == rule_id), None) if uc else None
        if rule:
            add("upward", "%s %s: %s" % (uc_id, rule_id, rule.name), "rule", target, target, "specification", uc.path, rule.line)
        else:
            add("upward", "%s does not define %s" % (uc_id, rule_id), "missing", target, None, "specification")
        if uc:
            for line, other, cited, where in uc.citations:
                if cited == rule_id and (other in (None, uc_id)):
                    add("sideways", "%s:%d  cited in %s %s" % (index.rel(uc.path), line, uc_id, where), "cites",
                        index.element_at(uc.path, line), target, "citation", uc.path, line)
            for other_uc in index.use_cases:
                for line, other, cited, where in other_uc.citations:
                    if other == uc_id and cited == rule_id and other_uc.id != uc_id:
                        add("sideways", "%s:%d  cited by %s %s" % (index.rel(other_uc.path), line, other_uc.id, where),
                            "cites", index.element_at(other_uc.path, line), target, "citation", other_uc.path, line)
            journeys(uc_id)
            markers(target, uc_id, model.unit_pattern(rule_id))
    elif re.fullmatch(r"UC-\d{3}", term):
        kind = "use_case"
        uc = by_id.get(term)
        if not uc:
            add("upward", "%s has no specification" % term, "missing", term, None, "specification")
        else:
            for rid in uc.requirement_ids:
                add("upward", "%s linked on its Requirements line" % rid, "links", term, rid, "requirements_line",
                    uc.path, uc.field_line("Requirements"))
            cited = re.compile(r"\b%s\s+BR-\d{3}\b" % re.escape(term))
            for path, line, text in index.text_mentions(cited, skip=uc.path):
                add("sideways", "%s:%d  %s" % (index.rel(path), line, text.strip()[:100]), "cites",
                    index.element_at(path, line), " ".join(cited.search(text).group(0).split()), "text", path, line)
            for line, other, rule_id, where in uc.citations:
                if other and other != term:
                    add("sideways", "%s:%d  %s %s depends on %s %s" % (index.rel(uc.path), line, term, where, other, rule_id),
                        "cites", index.element_at(uc.path, line), "%s %s" % (other, rule_id), "citation", uc.path, line)
            journeys(term)
            markers(term, term)
    elif re.fullmatch(r"TC-\d{3}", term):
        kind = "journey"
        tc = next((t for t in index.test_cases if t.id == term), None)
        if not tc:
            add("upward", "%s has no document" % term, "missing", term, None, "journey")
        else:
            for uc_id in tc.use_case_ids():
                add("upward", "%s used in its flow" % uc_id, "includes", term, uc_id, "journey", tc.path, tc.field_line("use_cases"))
            markers(term, term)
    else:
        kind = "noun"
        words = re.escape(term.strip()).replace(r"\ ", r"[\s_]+")
        pattern = re.compile(r"(?<![A-Za-z])%ss?(?![A-Za-z])" % words, re.IGNORECASE)
        if index.entities:
            model_file = index.docs.entity_model
            for name, entity in index.entities.entities.items():
                if pattern.search(name.replace("_", " ")):
                    add("upward", "%s:%d  entity %s: %s" % (index.rel(model_file), entity.line, name, entity.description),
                        "entity", term, name, "entity_model", model_file, entity.line)
                for line, row, _ in entity.attributes:
                    if pattern.search(row.get("Attribute", "").replace("_", " ")):
                        add("upward", "%s:%d  attribute %s.%s" % (index.rel(model_file), line, name, row.get("Attribute")),
                            "attribute", term, "%s.%s" % (name, row.get("Attribute")), "entity_model", model_file, line)
        if not result["upward"]:
            add("upward", "'%s' is not an entity or attribute of the entity model" % term, "missing", term, None, "entity_model")
        for path, line, text in index.text_mentions(pattern):
            add("sideways", "%s:%d  %s" % (index.rel(path), line, text.strip()[:100]), "mentions",
                index.element_at(path, line), term, "text", path, line)
    result["term_kind"] = kind
    for group in ("upward", "sideways", "downward"):
        result[group + "_items"] = typed[group]
    return result


def main(argv):
    parser = argparse.ArgumentParser(description="List what refers to an identifier or a business noun.")
    parser.add_argument("terms", nargs="+")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--code", default=".")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    args.docs = args.docs or model.docs_default()
    docs_model = model.Docs(args.docs)
    # A list or a measure cannot be made without the file: an unreadable one stops it with 1.
    stop = model.stop_if_old(docs_model, strict=True)
    if stop:
        return stop
    for folder in (args.docs, args.code):
        if not os.path.isdir(folder):
            print("no such folder: %s" % folder, file=sys.stderr)
            return 2
    try:
        index = Index(args.docs, args.code)
    except (OSError, UnicodeDecodeError) as exc:
        print("cannot read the specifications: %s" % exc, file=sys.stderr)
        return 2
    results = [impact_of(term, index) for term in args.terms]
    if args.format == "json":
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0
    for result in results:
        print("== %s" % result["term"])
        for group in ("upward", "sideways", "downward"):
            print("%s:" % group)
            for item in result[group] or ["(nothing)"]:
                print("  %s" % item)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
