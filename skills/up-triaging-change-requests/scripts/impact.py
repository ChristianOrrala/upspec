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

Exit code 0, 2 on usage errors.

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
        hits = []
        for path, line, text in model.find_markers(self.code_dir, uc_id):
            if os.path.abspath(path).startswith(self.docs_abs + os.sep):
                continue
            if extra is None or extra.search(text):
                hits.append("%s:%d  %s" % (self.rel(path), line, text.strip()[:100]))
        return hits

    def journeys_with(self, uc_id):
        return ["%s %s (%s)" % (tc.id, tc.title, tc.field("Status")) for tc in self.test_cases if uc_id in tc.use_case_ids()]

    def text_mentions(self, pattern, skip=None):
        """Lines in specifications that match the pattern: [(label, path, line, text)]."""
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
                    found.append("%s:%d  %s" % (self.rel(path), number, text.strip()[:100]))
        return found


def impact_of(term, index):
    up, side, down = [], [], []
    by_id = {u.id: u for u in index.use_cases if u.id}
    qualified = re.fullmatch(r"(UC-\d{3})\s+(BR-\d{3})", term)
    if re.fullmatch(r"(?:FR|NFR|C)-\d{3}", term):
        req = next((r for r in index.requirements if r.id == term), None)
        up.append("%s %s (Status %s)" % (term, req.title, req.status) if req else "%s is not in the catalog" % term)
        for uc in index.use_cases:
            if term in uc.requirement_ids:
                side.append("%s %s (Status %s) links it" % (uc.id, uc.name, uc.status))
                down += index.journeys_with(uc.id)
    elif qualified:
        uc_id, rule_id = qualified.groups()
        uc = by_id.get(uc_id)
        rule = next((r for r in uc.rules if r.id == rule_id), None) if uc else None
        up.append("%s %s: %s" % (uc_id, rule_id, rule.name) if rule else "%s does not define %s" % (uc_id, rule_id))
        if uc:
            for line, other, cited, where in uc.citations:
                if cited == rule_id and (other in (None, uc_id)):
                    side.append("%s:%d  cited in %s %s" % (index.rel(uc.path), line, uc_id, where))
            for other_uc in index.use_cases:
                for line, other, cited, where in other_uc.citations:
                    if other == uc_id and cited == rule_id and other_uc.id != uc_id:
                        side.append("%s:%d  cited by %s %s" % (index.rel(other_uc.path), line, other_uc.id, where))
            down += index.journeys_with(uc_id)
            down += index.code_hits(uc_id, model.unit_pattern(rule_id))
    elif re.fullmatch(r"UC-\d{3}", term):
        uc = by_id.get(term)
        if not uc:
            up.append("%s has no specification" % term)
        else:
            up += ["%s linked on its Requirements line" % rid for rid in uc.requirement_ids]
            cited = re.compile(r"\b%s\s+BR-\d{3}\b" % re.escape(term))
            side += index.text_mentions(cited, skip=uc.path)
            for line, other, rule_id, where in uc.citations:
                if other and other != term:
                    side.append("%s:%d  %s %s depends on %s %s" % (index.rel(uc.path), line, term, where, other, rule_id))
            down += index.journeys_with(term)
            down += index.code_hits(term)
    elif re.fullmatch(r"TC-\d{3}", term):
        tc = next((t for t in index.test_cases if t.id == term), None)
        if not tc:
            up.append("%s has no document" % term)
        else:
            up += ["%s used in its flow" % u for u in tc.use_case_ids()]
            down += index.code_hits(term)
    else:
        words = re.escape(term.strip()).replace(r"\ ", r"[\s_]+")
        pattern = re.compile(r"(?<![A-Za-z])%ss?(?![A-Za-z])" % words, re.IGNORECASE)
        if index.entities:
            for name, entity in index.entities.entities.items():
                if pattern.search(name.replace("_", " ")):
                    up.append("%s:%d  entity %s: %s" % (index.rel(index.docs.entity_model), entity.line, name, entity.description))
                for line, row, _ in entity.attributes:
                    if pattern.search(row.get("Attribute", "").replace("_", " ")):
                        up.append("%s:%d  attribute %s.%s" % (index.rel(index.docs.entity_model), line, name, row.get("Attribute")))
        if not up:
            up.append("'%s' is not an entity or attribute of the entity model" % term)
        side += index.text_mentions(pattern)
    return {"term": term, "upward": up, "sideways": side, "downward": down}


def main(argv):
    parser = argparse.ArgumentParser(description="List what refers to an identifier or a business noun.")
    parser.add_argument("terms", nargs="+")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--code", default=".")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    args.docs = args.docs or model.docs_default()
    docs_model = model.Docs(args.docs)
    stop = model.stop_if_old(docs_model)
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
