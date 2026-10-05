#!/usr/bin/env python3
"""Check use case specification files, one at a time, for structure and the closed loop.

ERROR  the file cannot be relied on: a missing title, field or section, an invalid
       Status or identifier, a cited rule that is not defined, an anchor or a
       continuation that names a step that does not exist.
WARN   a writing rule is broken: numbering, step count, actor as first word,
       "checks whether", a validation no flow answers, a flow without anchor or
       ending, empty postconditions, an uncited rule, weak or mechanism words,
       names and figures from the implementation, a specification too large to
       review, a retired rule that is still cited, an emoji (screen copy).
INFO   worth a look, never a failure: screen detail, a quantity without boundary
       examples, a mechanism word the entity model defines as a business noun, a
       long quotation of screen wording.

Output: path:line: SEVERITY CODE [element]: message
Exit code 0 when clean, 1 on any ERROR (with --strict also on any WARN), 2 on usage errors.

Usage:
    validate_use_case.py [--docs DIR] [--strict] FILE...

--docs names the docs folder (default: the parent of the folder holding the first
file). It is read for the entity model, to tell business nouns from mechanism
words, and for the requirements catalog, to know whether a Requirements line is due.

Requires Python 3.9+, standard library only. Reads files as data; writes nothing.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model  # noqa: E402  (local module, same folder)

REQUIRED_FIELDS = ("Use Case ID", "Use Case Name", "Primary Actor", "Goal", "Status")
REQUIRED_SECTIONS = ("Overview", "Main Success Scenario", "Alternative Flows", "Postconditions")
EXPECTED_SECTIONS = ("Preconditions", "Business Rules")
MIN_STEPS, MAX_STEPS = 3, 9     # the method's bound for a main success scenario
# Size a stakeholder can skim and an engineer can review in one sitting. Measured on a real
# project: specifications readers judged readable had a median of about 100 lines, 4 flows
# and 6 rules; the ones they judged too long to review had 270 to 460 lines, 16 to 25 flows
# and 20 to 34 rules, most of it detail of the implementation. That detail has its own check
# now (IMPLEMENTATION_DETAIL), so size is a hint from the first threshold and a warning only
# at double, as the owner set it.
HINT_LINES, HINT_FLOWS, HINT_RULES = 250, 12, 15
MAX_SPEC_LINES, MAX_FLOWS, MAX_RULES = 500, 24, 30
QUANTITY = re.compile(r"\b(at most|at least|no more than|fewer than|more than|less than|within|up to|until|"
                      r"maximum|minimum|not before|not after|\d+)\b", re.IGNORECASE)
# Screen copy. A specification says what a message tells the actor and quotes the exact words
# only where a rule depends on them, which are short (a keyword, a notice's title). In the third
# real-project trial the quoted messages that judges found made specifications hard to read ran
# from 13 to 30 words, emoji included.
QUOTE_WORDS = 12
QUOTED = re.compile(r'"([^"\n]+)"|“([^”\n]+)”|«([^»\n]+)»')
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF]")
# A reaction of the system, as opposed to a state that stays true.
REACTION = re.compile(r"\b(?:displays?|shows?|informs?|notif(?:y|ies)|sends?)\b|\b(?:error|warning)\s+message\b", re.IGNORECASE)


def _first_words_ok(text, actors):
    """True when the sentence starts with a declared actor, 'System' or 'Use case'."""
    plain = re.sub(r"^(?:The|A|An)\s+", "", text.strip(), flags=re.IGNORECASE)
    for name in list(actors) + ["System", "Use case"]:
        if re.match(re.escape(name) + r"(?:'s)?\b", plain, re.IGNORECASE):
            return True
    return False


def check_use_case(uc, report, entity_nouns=(), catalog_exists=False):
    """Append findings for one parsed use case to the reporter."""
    path, uid = uc.path, uc.id or os.path.basename(uc.path)
    if uc.title is None:
        report.error(path, 1, "TITLE_MISSING", uid, "no '# Use Case: <name>' title")
    for section in REQUIRED_SECTIONS:
        if section not in uc.section_lines:
            report.error(path, 0, "SECTION_MISSING", uid, "section '## %s' is missing" % section)
    for section in EXPECTED_SECTIONS:
        if section not in uc.section_lines:
            report.warn(path, 0, "SECTION_MISSING", uid, "section '## %s' is missing" % section)
    for label in REQUIRED_FIELDS:
        if not uc.field(label):
            report.error(path, uc.section_lines.get("Overview", 0), "FIELD_MISSING", uid, "Overview has no **%s:** value" % label)
    id_text, id_line = uc.fields.get("Use Case ID", ("", 0))
    if id_text and not re.fullmatch(r"UC-\d{3}", id_text.strip()):
        report.error(path, id_line, "ID_FORMAT", uid, "identifier must be UC- and three digits, got '%s'" % id_text)
    status, status_line = uc.status, uc.fields.get("Status", ("", 0))[1]
    if uc.field("Status") and status not in model.UC_STATUSES:
        report.error(path, status_line, "STATUS_INVALID", uid, "Status '%s' is not one of %s" % (uc.field("Status"), ", ".join(model.UC_STATUSES)))
    if uc.id and uc.name:
        expected = "%s-%s.md" % (uc.id, model.kebab(uc.name))
        if os.path.basename(path) != expected:
            report.warn(path, 0, "FILE_NAME", uid, "file should be named %s" % expected)
    if not uc.field("Trigger"):
        report.warn(path, uc.section_lines.get("Overview", 0), "TRIGGER_MISSING", uid, "Overview has no **Trigger:** naming the event that starts the use case")
    if re.fullmatch(r"(the )?system", uc.field("Primary Actor").strip(), re.IGNORECASE):
        report.warn(path, uc.fields["Primary Actor"][1], "PRIMARY_ACTOR_SYSTEM", uid, "the system is never the primary actor; name the role or the time or external system that starts the use case")
    req_ids = uc.requirement_ids
    if catalog_exists and not any(r.startswith("FR-") for r in req_ids):
        report.warn(path, uc.fields.get("Requirements", ("", uc.section_lines.get("Overview", 0)))[1], "REQUIREMENTS_LINE", uid,
                    "no **Requirements:** line that links at least one functional requirement")

    # main success scenario
    numbers = [s.number for s in uc.steps]
    if numbers and numbers != list(range(1, len(numbers) + 1)):
        report.warn(path, uc.steps[0].line, "STEP_NUMBERING", uid, "steps must be numbered from 1 without gaps, got %s" % numbers)
    if "Main Success Scenario" in uc.section_lines and not MIN_STEPS <= len(uc.steps) <= MAX_STEPS:
        report.warn(path, uc.section_lines["Main Success Scenario"], "STEP_COUNT", uid,
                    "%d steps; a main success scenario has %d to %d. More usually means screen mechanics or a goal too low, fewer means missing validations or state changes" % (len(uc.steps), MIN_STEPS, MAX_STEPS))
    actors = uc.actors
    for step in uc.steps:
        element = "%s step %d" % (uid, step.number)
        if actors and not _first_words_ok(step.text, actors):
            report.warn(path, step.line, "STEP_ACTOR", element, "the first word must be who acts: a declared actor or System")
        if re.match(r"^\s*If\b", step.text):
            report.warn(path, step.line, "STEP_IF", element, "main scenario steps succeed; move the condition into an alternative flow")
    for line, text, where in uc.all_step_texts():
        if re.search(r"\bchecks?\s+(?:whether|if)\b", text, re.IGNORECASE):
            report.warn(path, line, "CHECKS_WHETHER", "%s %s" % (uid, where), "write 'validates that ...' and put the failure in a named alternative flow")
        for term in model.pattern_hits(text, model.UI_TERMS):
            report.info(path, line, "UI_DETAIL", "%s %s" % (uid, where), "'%s' is screen detail; say what the actor decides, enters or learns" % term)

    # alternative flows and the closed loop
    step_numbers = set(numbers)
    answered = {}
    flows_by_label = {f.label: f for f in uc.flows}
    for flow in uc.flows:
        element = "%s %s" % (uid, flow.label)
        if not re.fullmatch(r"A\d+", flow.label):
            report.warn(path, flow.line, "FLOW_LABEL", uid, "flow heading must read '### A<n>: <name of the condition>'")
        if flow.retired:
            continue                      # keeps its label so the identifier is never reused
        for label, number in flow.trigger_flow_steps:
            other = flows_by_label.get(label)
            if other is None or other.retired or other is flow:
                report.error(path, flow.trigger_line, "FLOW_ANCHOR_INVALID", element, "trigger names %s step %d; that flow does not exist here" % (label, number))
            elif number not in [s.number for s in other.steps]:
                report.error(path, flow.trigger_line, "FLOW_ANCHOR_INVALID", element, "trigger names %s step %d, which %s does not have" % (label, number, label))
        if not flow.trigger:
            report.warn(path, flow.line, "FLOW_TRIGGER", element, "flow has no **Trigger:** line")
        elif not flow.trigger_steps and not flow.trigger_flow_steps and not flow.any_time:
            report.warn(path, flow.trigger_line, "FLOW_ANCHOR", element, "trigger must name the step it diverges from as (step N), (A2 step N) for a step of another flow, or say 'at any time'")
        for number in flow.trigger_steps:
            answered.setdefault(number, []).append(flow.label)
            if step_numbers and number not in step_numbers:
                report.error(path, flow.trigger_line, "FLOW_ANCHOR_INVALID", element, "trigger names step %d, which the main scenario does not have" % number)
        if not flow.steps:
            report.warn(path, flow.line, "FLOW_EMPTY", element, "flow has no steps")
        if flow.ending is None:
            report.warn(path, flow.line, "FLOW_ENDING", element, "flow must end with 'Use case continues at step N.' or 'Use case ends.'")
        elif flow.ending[0] == "continues" and step_numbers and flow.ending[1] not in step_numbers:
            report.error(path, flow.ending_line, "CONTINUE_INVALID", element, "continues at step %d, which the main scenario does not have" % flow.ending[1])
    labels = [f.label for f in uc.flows if re.fullmatch(r"A\d+", f.label)]
    if labels and labels != ["A%d" % i for i in range(1, len(labels) + 1)]:
        report.warn(path, uc.flows[0].line, "FLOW_LABEL", uid, "flows must be labeled A1, A2, ... in order, got %s" % ", ".join(labels))
    if "Alternative Flows" in uc.section_lines and not uc.flows and not uc.flows_placeholder:
        report.warn(path, uc.section_lines["Alternative Flows"], "NO_ALTERNATIVE_FLOWS", uid,
                    "no alternative flow; if no step can fail or branch, say so in one italic line")
    for step in uc.steps:
        if re.search(r"\bvalidates\b", step.text, re.IGNORECASE):
            flows = answered.get(step.number, [])
            element = "%s step %d" % (uid, step.number)
            if not flows:
                report.warn(path, step.line, "VALIDATION_UNANSWERED", element, "no alternative flow answers this validation; add one whose trigger names (step %d)" % step.number)
            elif len(flows) > 1:
                report.info(path, step.line, "VALIDATION_MULTI", element, "answered by %s; one validation normally has one flow" % ", ".join(flows))

    # postconditions
    if "Postconditions" in uc.section_lines:
        if not uc.success:
            report.warn(path, uc.section_lines["Postconditions"], "POSTCONDITIONS_EMPTY", uid, "no success postcondition")
        if not uc.failure:
            report.warn(path, uc.section_lines["Postconditions"], "POSTCONDITIONS_EMPTY", uid,
                        "no failure postcondition; state what stays true on every unsuccessful end")
    for line, text in uc.failure:
        if REACTION.search(text):
            report.warn(path, line, "POSTCONDITION_REACTION", uid, "a failure postcondition is a guarantee, not a reaction; messages belong in the alternative flow")

    # size
    live_flows = [f for f in uc.flows if not f.retired]
    live_rules = [r for r in uc.rules if not r.retired]
    sizes = ((uc.line_count, HINT_LINES, MAX_SPEC_LINES, "lines"), (len(live_flows), HINT_FLOWS, MAX_FLOWS, "alternative flows"),
             (len(live_rules), HINT_RULES, MAX_RULES, "business rules"))
    over = ["%d %s (at most %d)" % (n, what, limit) for n, _, limit, what in sizes if n > limit]
    near = ["%d %s (hint from %d)" % (n, what, hint) for n, hint, limit, what in sizes if hint < n <= limit]
    if over:
        report.warn(path, uc.title_line or 1, "SPEC_SIZE", uid,
                    "%s: too large for a stakeholder to skim or an engineer to review. Check the goal level (one goal or several, a step "
                    "of something larger), keep alternative flows to outcomes an actor can tell apart, and move limits of the "
                    "implementation to the recovery ledger or an NFR row" % ", ".join(over))
    elif near:
        report.info(path, uc.title_line or 1, "SPEC_SIZE", uid,
                    "%s: still reviewable, but check that it is one goal and that every flow is an outcome the actor can tell apart" % ", ".join(near))

    # business rules
    defined = [r.id for r in uc.rules]
    wanted = ["BR-%03d" % i for i in range(1, len(defined) + 1)]
    if defined and defined != wanted:
        report.warn(path, uc.rules[0].line, "RULE_NUMBERING", uid, "rules must be numbered %s, got %s" % (", ".join(wanted), ", ".join(defined)))
    retired = {r.id for r in uc.rules if r.retired}
    cited_here = set()
    for line, other_uc, rule_id, where in uc.citations:
        if other_uc and other_uc != uc.id:
            continue                      # qualified citation of another use case; the cross-file lint resolves it
        cited_here.add(rule_id)
        if rule_id not in defined:
            report.error(path, line, "RULE_UNDEFINED", "%s %s" % (uid, where), "%s is cited but not defined in this use case" % rule_id)
        elif rule_id in retired:
            report.warn(path, line, "RULE_RETIRED_CITED", "%s %s" % (uid, where), "%s is retired; cite the rule that replaced it, or drop the citation" % rule_id)
    for rule in uc.rules:
        element = "%s %s" % (uid, rule.id)
        text = rule.text()
        if rule.retired:
            if not text:
                report.warn(path, rule.line, "RULE_EMPTY", element, "a retired rule says in one line where it went or why it was dropped")
            continue
        if not text:
            report.warn(path, rule.line, "RULE_EMPTY", element, "rule has no statement")
        if rule.id not in cited_here:
            report.warn(path, rule.line, "RULE_UNCITED", element, "rule is cited by no step or flow")
        if text and QUANTITY.search(text) and not re.search(r"\bExamples?\s*:", text):
            report.info(path, rule.line, "RULE_BOUNDARY", element, "rule has a quantity or date but no 'Examples:' line that settles the boundary")

    # wording
    nouns = {n.lower() for n in entity_nouns}
    passages = [(line, text, where) for line, text, where in uc.all_step_texts()]
    passages += [(f.trigger_line, f.trigger, f.label) for f in uc.flows if f.trigger and not f.retired]
    passages += [(line, text, "precondition") for line, text in uc.preconditions]
    passages += [(line, text, "postcondition") for line, text in uc.success + uc.failure]
    passages += [(line, text, r.id) for r in uc.rules if not r.retired for line, text in r.body if text.strip()]
    for label in ("Goal", "Trigger"):
        if uc.field(label):
            passages.append((uc.fields[label][1], uc.field(label), label))
    for line, text, where in passages:
        element = "%s %s" % (uid, where)
        for word in model.word_hits(text, model.WEAK_WORDS):
            report.warn(path, line, "WEAK_WORD", element, "'%s' leaves a decision open; state the rule or the observable outcome" % word)
        for term in model.pattern_hits(text, model.MECHANISM_TERMS):
            if term.lower() in nouns:
                report.info(path, line, "MECHANISM_TERM", element, "'%s' is a mechanism word, accepted because the entity model defines it as a business noun" % term)
            else:
                report.warn(path, line, "MECHANISM_TERM", element, "'%s' says how the system is built; state what the actor and the system achieve" % term)
        for term in model.pattern_hits(text, model.IMPLEMENTATION_TERMS):
            report.warn(path, line, "IMPLEMENTATION_DETAIL", element,
                        "%s from the implementation; say it in business words, and keep the code's value in the recovery ledger or an NFR row" % term)
        if EMOJI.search(text):
            report.warn(path, line, "SCREEN_COPY", element, "an emoji is screen copy; say what the message tells the actor")
        for match in QUOTED.finditer(text):
            quoted = next(g for g in match.groups() if g is not None)
            if len(quoted.split()) > QUOTE_WORDS:
                report.info(path, line, "SCREEN_COPY", element,
                            "a quotation of %d words; say what the message tells the actor, and quote exact words only where a rule depends on them" % len(quoted.split()))


def validate_files(paths, docs_dir=None, report=None):
    report = report or model.Reporter(os.getcwd())
    nouns, catalog = set(), False
    if docs_dir and os.path.isdir(docs_dir):
        docs = model.Docs(docs_dir)
        catalog = bool(docs.requirements)
        if docs.entity_model:
            try:
                nouns = model.parse_entity_model(docs.entity_model).nouns()
            except OSError as exc:
                report.info(docs.entity_model, 0, "ENTITY_MODEL_UNREADABLE", "-", str(exc))
    for path in paths:
        try:
            check_use_case(model.parse_use_case(path), report, nouns, catalog)
        except (OSError, UnicodeDecodeError) as exc:
            report.error(path, 0, "UNREADABLE", "-", "cannot read the file: %s" % exc)
    return report


def main(argv):
    parser = argparse.ArgumentParser(description="Check use case specification files.")
    parser.add_argument("files", nargs="+")
    parser.add_argument("--docs", help="docs folder (default: parent of the first file's folder)")
    parser.add_argument("--strict", action="store_true", help="fail on warnings too")
    args = parser.parse_args(argv)
    docs_dir = args.docs or os.path.dirname(os.path.dirname(os.path.abspath(args.files[0])))
    report = validate_files(args.files, docs_dir)
    report.print_text()
    return report.exit_code(args.strict)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
