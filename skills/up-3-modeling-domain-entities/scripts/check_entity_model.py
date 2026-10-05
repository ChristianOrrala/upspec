#!/usr/bin/env python3
"""Check an entity model: diagram and sections agree, cells use the vocabulary,
lifecycles are consistent, and avoided words are not used in the specifications.

ERROR  no erDiagram; an entity of the diagram has no section; a section appears
       twice; a foreign key names an entity that does not exist.
WARN   attributes inside the diagram; a heading that is not UPPER_SNAKE_CASE; a
       missing description; wrong table columns; a data type or validation phrase
       outside the vocabulary; an empty validation cell; a foreign key without a
       relationship line; a state attribute without a lifecycle; a lifecycle
       state that is not an allowed value; an avoided word used in a specification.
INFO   a section that is not in the diagram; a relationship without a foreign key.

Output: path:line: SEVERITY CODE [element]: message
Exit code 0 when clean, 1 on any ERROR (with --strict also on any WARN), 2 on usage errors.

Usage:
    check_entity_model.py [--docs DIR] [--strict]      (default DIR: docs)

Requires Python 3.9+, standard library only. Reads files as data; writes nothing.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model  # noqa: E402  (local module, same folder)

COLUMNS = ["Attribute", "Description", "Data Type", "Length/Precision", "Validation Rules"]
PHRASES = (r"Primary Key", r"Sequence", r"Not Null", r"Optional", r"Unique", r"Foreign Key \(([A-Z][A-Z0-9_]*)\.\w+\)",
           r"Min: \S+", r"Max: \S+", r"Format: \w+")
STATE_NAMES = ("status", "state")


def split_rules(cell):
    """Split a Validation Rules cell into phrases; 'Values:' takes the rest of the cell."""
    head, values = cell, None
    match = re.search(r"\bValues:\s*(.*)$", cell)
    if match:
        head, values = cell[:match.start()], [v.strip() for v in match.group(1).split(",") if v.strip()]
    return [p.strip() for p in head.split(",") if p.strip()], values


def lifecycle_states(text):
    states = set()
    for chain in text.split(";"):
        states.update(s.strip() for s in re.split(r"→|->", chain) if s.strip())
    return states


def check(docs, report):
    path = docs.entity_model
    em = model.parse_entity_model(path)
    if not em.has_diagram:
        report.error(path, 0, "NO_DIAGRAM", "-", "no Mermaid erDiagram block")
    for line in em.diagram_attribute_lines:
        report.warn(path, line, "DIAGRAM_ATTRIBUTES", "-", "the diagram shows names and relationships only; attributes belong in the entity's table")
    for line, name in em.duplicates:
        report.error(path, line, "DUPLICATE_ENTITY", name, "entity has a second section; define each entity once")
    for name, line in sorted(em.diagram_entities.items()):
        if name not in em.entities:
            report.error(path, line, "ENTITY_NO_SECTION", name, "entity is in the diagram but has no '### %s' section" % name)
    related = set()
    for line, left, right, _ in em.relationships:
        related.add(frozenset((left, right)))
    foreign = set()
    for name, entity in em.entities.items():
        if name not in em.diagram_entities:
            report.info(path, entity.line, "SECTION_NOT_IN_DIAGRAM", name, "entity has a section but is not in the diagram; list it there, on a line of its own if it has no relationship")
        if not re.fullmatch(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*", name):
            report.warn(path, entity.line, "HEADING_FORM", name, "entity headings are UPPER_SNAKE_CASE")
        if not entity.description:
            report.warn(path, entity.line, "NO_DESCRIPTION", name, "one sentence saying what the entity is")
        if entity.header and entity.header != COLUMNS:
            report.warn(path, entity.line, "TABLE_COLUMNS", name, "table columns must be: %s" % " | ".join(COLUMNS))
        if not entity.attributes:
            report.warn(path, entity.line, "NO_ATTRIBUTES", name, "entity has no attribute table")
        state_values = None
        for line, row, _ in entity.attributes:
            attribute = "%s.%s" % (name, row.get("Attribute", "?"))
            data_type = row.get("Data Type", "")
            if data_type and data_type not in model.DATA_TYPES:
                report.warn(path, line, "DATA_TYPE", attribute, "'%s' is not a business type; use one of %s" % (data_type, ", ".join(model.DATA_TYPES)))
            cell = row.get("Validation Rules", "")
            if not cell or cell in ("-", "N/A"):
                report.warn(path, line, "VALIDATION_EMPTY", attribute, "every attribute states at least Not Null, Optional or Primary Key")
                continue
            phrases, values = split_rules(cell)
            for phrase in phrases:
                if not any(re.fullmatch(p, phrase) for p in PHRASES):
                    report.warn(path, line, "VALIDATION_PHRASE", attribute, "'%s' is not a phrase of the validation vocabulary" % phrase)
                fk = re.fullmatch(PHRASES[5], phrase)
                if fk:
                    target = fk.group(1)
                    if target not in em.entities:
                        report.error(path, line, "REFERENCE_UNKNOWN", attribute, "foreign key names %s, which has no section" % target)
                    else:
                        foreign.add(frozenset((name, target)))
                        if frozenset((name, target)) not in related and name != target:
                            report.warn(path, line, "FK_NO_RELATIONSHIP", attribute, "no relationship line between %s and %s in the diagram" % (name, target))
            if row.get("Attribute", "").lower() in STATE_NAMES and values:
                state_values = (line, values)
        if state_values and not entity.lifecycle:
            report.warn(path, state_values[0], "LIFECYCLE_MISSING", name, "the entity has states %s but no **Lifecycle:** line saying which moves are allowed" % ", ".join(state_values[1]))
        if entity.lifecycle:
            line, text = entity.lifecycle
            states = lifecycle_states(text)
            if state_values:
                for state in sorted(states - set(state_values[1])):
                    report.warn(path, line, "LIFECYCLE_STATE", name, "lifecycle state '%s' is not one of the attribute's values" % state)
                for value in sorted(set(state_values[1]) - states):
                    report.warn(path, line, "LIFECYCLE_STATE", name, "value '%s' appears in no lifecycle chain" % value)
    for line, left, right, _ in em.relationships:
        if frozenset((left, right)) not in foreign and left != right:
            report.info(path, line, "RELATIONSHIP_NO_FK", "%s-%s" % (left, right), "relationship has no foreign key attribute on either side")

    # avoided words in the specifications
    avoided = [(word, name) for name, entity in em.entities.items() for word in entity.avoid]
    if avoided:
        files = [f for f in [docs.requirements] + docs.use_case_files() + docs.test_case_files() if f]
        for spec in files:
            try:
                lines = model.read_lines(spec)
            except (OSError, UnicodeDecodeError):
                continue
            for number, text in model.outside_fences(lines):
                for word, name in avoided:
                    if model.word_hits(text, [word]) or model.word_hits(text, [word + "s"]):
                        report.warn(spec, number, "AVOIDED_WORD", name, "'%s' is an avoided word; the model's term is %s" % (word, name.replace("_", " ").lower()))


def main(argv):
    parser = argparse.ArgumentParser(description="Check an entity model.")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--strict", action="store_true", help="fail on warnings too")
    args = parser.parse_args(argv)
    args.docs = args.docs or model.docs_default()
    if not os.path.isdir(args.docs):
        print("no such folder: %s" % args.docs, file=sys.stderr)
        return 2
    docs = model.Docs(args.docs)
    report = model.Reporter(os.getcwd())
    if not docs.entity_model:
        print("no entity model in %s (expected entity_model.md)" % args.docs, file=sys.stderr)
        return 2
    try:
        check(docs, report)
    except (OSError, UnicodeDecodeError) as exc:
        report.error(docs.entity_model, 0, "UNREADABLE", "-", "cannot read the file: %s" % exc)
    report.print_text()
    return report.exit_code(args.strict)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
