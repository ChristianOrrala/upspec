#!/usr/bin/env python3
"""Draw a sample of recovered claims for a second reader to check against the code.

The verification pass of a recovery. A reader who did not write the
specifications takes the sample, opens each evidence location and gives two
verdicts: one for the claim (correct, wrong, partly right, not found) and one
for its ledger row (decides: the cited line is where the claim is decided and
the note describes this element; near; wrong). Wrong and partly right claims
and rows that do not decide are fixed; checked claims become `verified` rows in
the ledger; then a new sample is drawn (another seed) until one comes back
clean: every claim correct and every row deciding.

Claims are every business rule and alternative flow of the specifications,
every failure postcondition and every success postcondition that promises an
absolute (never, always, only, every, any, nothing, none), every entity's
identifier and required attributes with their types, and every entity
lifecycle. A rule or a guarantee is checked by looking for a way around it:
another entry point, flow or state that reaches the same outcome without the
check. A claim that holds at the cited line but has a way around it is wrong.
A guarantee is also read against the rest of its own specification: a flow
that does what the guarantee rules out makes it wrong. Elements whose ledger row is already `verified`
are left out. A third of the sample comes from the entity model when it has
claims, because that is where recovered guesses gather.

Usage:
    sample_claims.py [--docs DIR] [--ledger FILE] [--count N] [--seed S] [--format md|json]

--ledger defaults to DIR/recovery/ledger.md. Exit code 0, 2 on usage errors.

Requires Python 3.9+, standard library only. Reads files as data; writes nothing.
"""
import argparse
import json
import math
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model  # noqa: E402  (local module, same folder)

# Ten claims is what one reader checks in a sitting; the independent judges of the
# first real-project trial found the recovery's errors with samples of ten to twelve.
DEFAULT_COUNT = 10
# In that trial most wrong statements of short recovered specifications were in the
# entity model (required fields, states nothing writes), so it gets a fixed share.
ENTITY_SHARE = 1 / 3
CLAIM_CHARS = 300        # enough for a rule and its examples; the reader opens the file for the rest
REQUIRED = re.compile(r"\b(?:primary key|not null|required)\b", re.IGNORECASE)
# The words of a promise without exceptions. In the third trial on a real project the
# contradictions the records missed were such promises broken by a flow of the same use
# case ("never reveals an account" against a reset flow that does).
# In the fourth trial a verified rule ("reveals nothing about which accounts exist") held at
# its cited line and was broken by another path; "nothing" and "none" promise as much.
ABSOLUTE = re.compile(r"\b(?:never|always|only|every|any|no one|nobody|nothing|none)\b", re.IGNORECASE)


def ledger_rows(path):
    """Element -> (evidence, state, note) from the ledger tables."""
    rows = {}
    if not path or not os.path.isfile(path):
        return rows
    for table in model.read_tables(model.read_lines(path)):
        if not table["header"] or table["header"][0].strip().lower() != "element":
            continue
        for _, row, _ in table["rows"]:
            element = row.get(table["header"][0], "").strip().strip("`")
            if element and not element.startswith("["):
                rows[element] = (row.get("Evidence", "").strip(), row.get("State", "").strip().lower(), row.get("Note", "").strip())
    return rows


def short(text):
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= CLAIM_CHARS else text[:CLAIM_CHARS - 1] + "…"


def typed(row):
    """An attribute with its type, as the reader checks it: 'id (String 36, Primary Key)'."""
    kind = " ".join(v for v in (row.get("Data Type", "").strip(), row.get("Length/Precision", "").strip()) if v and v != "-")
    key = ", Primary Key" if "primary key" in row.get("Validation Rules", "").lower() else ""
    return "%s (%s%s)" % (row.get("Attribute", "?"), kind or "no type", key)


def claims(docs):
    """(use case claims grouped by use case, entity claims): each claim a dict with element and text."""
    by_use_case = {}
    for uc in model.load_use_cases(docs):
        if not uc.id:
            continue
        items = [{"element": "%s %s" % (uc.id, r.id), "claim": short("%s: %s" % (r.name, r.text()))} for r in uc.rules if not r.retired]
        items += [{"element": "%s %s" % (uc.id, f.label), "claim": short("%s. Trigger: %s" % (f.name, f.trigger))} for f in uc.flows if not f.retired]
        for prefix, conditions, every in (("Post-S", uc.success, False), ("Post-F", uc.failure, True)):
            items += [{"element": "%s %s-%d" % (uc.id, prefix, number), "claim": short("Guarantee: %s" % text)}
                      for number, (_, text) in enumerate(conditions, 1) if every or ABSOLUTE.search(text)]
        if items:
            by_use_case[uc.id] = items
    entity_claims = []
    if docs.entity_model:
        for name, entity in model.parse_entity_model(docs.entity_model).entities.items():
            required = [typed(row) for _, row, _ in entity.attributes if REQUIRED.search(row.get("Validation Rules", ""))]
            if required:
                entity_claims.append({"element": "ENTITY %s required" % name, "claim": short("Always present, with these types: %s" % ", ".join(required))})
            if entity.lifecycle:
                entity_claims.append({"element": "ENTITY %s lifecycle" % name, "claim": short("Lifecycle: %s" % entity.lifecycle[1])})
    return by_use_case, entity_claims


def draw(by_use_case, entity_claims, ledger, count, seed):
    """Pick the sample, leaving out verified elements. Returns (sample, number of unverified claims)."""
    rng = random.Random(seed)
    open_ = lambda item: ledger.get(item["element"], ("", "", ""))[1] != "verified"
    entities = [c for c in entity_claims if open_(c)]
    groups = {uc: [c for c in items if open_(c)] for uc, items in sorted(by_use_case.items())}
    groups = {uc: items for uc, items in groups.items() if items}
    pool_size = len(entities) + sum(len(items) for items in groups.values())
    rng.shuffle(entities)
    for items in groups.values():
        rng.shuffle(items)
    sample = entities[:min(len(entities), math.ceil(count * ENTITY_SHARE))]
    order = list(groups)
    rng.shuffle(order)
    while len(sample) < count and any(groups.values()):
        for uc in order:                       # one claim per use case per round: spread over every file
            if groups[uc] and len(sample) < count:
                sample.append(groups[uc].pop())
    rest = entities[len([c for c in sample if c["element"].startswith("ENTITY ")]):]
    sample += rest[:max(0, count - len(sample))]
    for item in sample:
        evidence, _, note = ledger.get(item["element"], ("", "", ""))
        item["evidence"] = evidence or "no ledger row: find it in the code"
        item["note"] = short(note) if note else ""
    return sample, pool_size


def main(argv):
    parser = argparse.ArgumentParser(description="Draw a sample of recovered claims for a second reader.")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--ledger")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--seed", type=int, default=1, help="use another seed for every round")
    parser.add_argument("--format", choices=("md", "json"), default="md")
    args = parser.parse_args(argv)
    args.docs = args.docs or model.docs_default()
    if not os.path.isdir(args.docs):
        print("no such folder: %s" % args.docs, file=sys.stderr)
        return 2
    if args.count < 1:
        print("--count must be at least 1", file=sys.stderr)
        return 2
    docs = model.Docs(args.docs)
    try:
        by_use_case, entity_claims = claims(docs)
        ledger = ledger_rows(args.ledger or os.path.join(args.docs, "recovery", "ledger.md"))
    except (OSError, UnicodeDecodeError) as exc:
        print("cannot read the specifications: %s" % exc, file=sys.stderr)
        return 2
    sample, pool = draw(by_use_case, entity_claims, ledger, args.count, args.seed)
    if args.format == "json":
        print(json.dumps({"seed": args.seed, "unverified": pool, "sample": sample}, indent=2, ensure_ascii=False))
        return 0
    print("## Verification sample (seed %d): %d of %d unverified claims" % (args.seed, len(sample), pool))
    print()
    if not sample:
        print("Every claim is verified.")
        return 0
    print("Check each claim against its evidence in the code. For a rule or a guarantee, also look for a way around it:")
    print("another entry point, flow or state that reaches the same outcome without the check; if there is one, the claim")
    print("is wrong, and the note says which path. Read each guarantee against the rest of its own specification too.")
    print("Claim verdict: correct, wrong, partly right, not found. A type that differs from the schema is wrong.")
    print("Row verdict: decides (the cited line is where the claim is decided, and the ledger note describes this")
    print("element), near, or wrong. The sample is clean only when every claim is correct and every row decides.")
    print("In the Note, quote the code line that decides the claim, or the path around it: a verdict without a quoted")
    print("line has not been checked.")
    print()
    print("| # | Element | Claim | Ledger note | Evidence | Claim verdict | Row verdict | Note |")
    print("|---|---|---|---|---|---|---|---|")
    for number, item in enumerate(sample, 1):
        print("| %d | %s | %s | %s | %s | | | |" % (number, item["element"], item["claim"].replace("|", "/"),
                                                    item["note"].replace("|", "/"), item["evidence"].replace("|", "/")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
