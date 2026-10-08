#!/usr/bin/env python3
"""Measure a specification set and show where it could be cut into bounded contexts.

Reports:
  counts     use cases, alternative flows, business rules, entities, actors, requirements
  usage      for every entity, the use cases whose text names it
  clusters   groups of use cases connected through shared entities
  bridges    entities whose removal separates a cluster into at least two groups
             of two or more use cases: the candidates for a contract between contexts,
             fewest users first (an entity most use cases of a group name is that
             group's core, not its boundary)
  links      rule citations and journey test cases that connect use cases; with
             --assign, which of them would cross the proposed cut

The numbers describe; they do not decide. Whether to split is the owner's decision.

Exit code 0, 2 on usage errors.

Usage:
    spec_core_metrics.py [--docs DIR] [--format text|json] [--assign FILE]

--assign FILE checks a proposed assignment: a text file with one line per element,
`<context> <identifier or ENTITY_NAME>`, for example `billing UC-003` or
`billing INVOICE`. The script reports elements assigned twice, elements not
assigned, entities used across contexts, and citations and journeys that cross.

Requires Python 3.9+, standard library only. Reads files as data; writes nothing.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model  # noqa: E402  (local module, same folder)


# A bridge is reported only when it leaves at least two groups of this size:
# a single use case cut off from the rest is a use case, not a candidate context.
MIN_GROUP = 2


def entity_pattern(name):
    words = [re.escape(w) for w in name.lower().split("_")]
    return re.compile(r"(?<![a-z])%s(?:e?s)?(?![a-z])" % r"[\s_-]+".join(words), re.IGNORECASE)


def use_case_text(uc):
    parts = [uc.field("Goal"), uc.field("Trigger")]
    parts += [text for _, text in uc.preconditions + uc.success + uc.failure]
    parts += [text for _, text, _ in uc.all_step_texts()]
    parts += [flow.trigger for flow in uc.flows]
    parts += [rule.name + " " + rule.text() for rule in uc.rules]
    return "\n".join(p for p in parts if p)


def components(use_case_ids, uses, without=()):
    """Group use cases that share an entity. uses: use case id -> set of entity names."""
    parent = {u: u for u in use_case_ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    by_entity = {}
    for uc_id in use_case_ids:
        for entity in uses.get(uc_id, ()):
            if entity not in without:
                by_entity.setdefault(entity, []).append(uc_id)
    for members in by_entity.values():
        for other in members[1:]:
            parent[find(other)] = find(members[0])
    groups = {}
    for uc_id in use_case_ids:
        groups.setdefault(find(uc_id), []).append(uc_id)
    return sorted((sorted(g) for g in groups.values()), key=lambda g: (-len(g), g))


def measure(docs):
    use_cases = [u for u in model.load_use_cases(docs) if u.id and u.status != "Obsolete"]
    entities = model.parse_entity_model(docs.entity_model).entities if docs.entity_model else {}
    requirements = model.parse_requirements(docs.requirements)[0] if docs.requirements else []
    journeys = [model.parse_test_case(p) for p in docs.test_case_files()]
    ids = [u.id for u in use_cases]
    by_id = {u.id: u for u in use_cases}
    patterns = {name: entity_pattern(name) for name in entities}
    uses = {}
    for uc in use_cases:
        text = use_case_text(uc)
        uses[uc.id] = {name for name, pattern in patterns.items() if pattern.search(text)}
    usage = {name: sorted(u for u in ids if name in uses[u]) for name in entities}
    clusters = components(ids, uses)
    bridges = []
    for name in sorted(entities):
        if len(usage[name]) < 2:
            continue
        without = components(ids, uses, without=(name,))
        if len(without) > len(clusters):
            home = next(c for c in clusters if usage[name][0] in c)
            parts = [g for g in without if g[0] in home]
            if sum(1 for g in parts if len(g) >= MIN_GROUP) >= 2:
                bridges.append({"entity": name, "used_by": len(usage[name]), "separates": parts})
    bridges.sort(key=lambda b: (b["used_by"], b["entity"]))    # fewest users first: the cheapest contract
    citations = sorted({(uc.id, other, rule) for uc in use_cases for _, other, rule, _ in uc.citations if other and other != uc.id})
    journey_links = [{"journey": tc.id, "use_cases": sorted(set(tc.use_case_ids()))} for tc in journeys if len(set(tc.use_case_ids())) > 1]
    actors = sorted({a for uc in use_cases for a in uc.actors})
    return {
        "counts": {"use_cases": len(use_cases), "alternative_flows": sum(len(u.flows) for u in use_cases),
                   "business_rules": sum(len(u.rules) for u in use_cases), "entities": len(entities), "actors": len(actors),
                   "requirements": len(requirements), "journey_test_cases": len(journeys)},
        "actors": actors,
        "usage": usage,
        "use_cases": {u: {"name": by_id[u].name, "actors": by_id[u].actors, "entities": sorted(uses[u]),
                          "requirements": by_id[u].requirement_ids} for u in ids},
        "use_cases_naming_no_entity": [u for u in ids if not uses[u]],
        "entities_named_by_no_use_case": sorted(name for name in entities if not usage[name]),
        "clusters": [{"use_cases": c, "entities": sorted({e for u in c for e in uses[u]}),
                      "actors": sorted({a for u in c for a in by_id[u].actors})} for c in clusters],
        "bridges": bridges,
        "citations": [{"from": a, "to": b, "rule": r} for a, b, r in citations],
        "journeys": journey_links,
        "requirement_ids": [r.id for r in requirements],
    }


def check_assignment(path, data):
    """Compare a proposed assignment with the measured set."""
    assigned, twice, unknown = {}, [], []
    known = set(data["use_cases"]) | set(data["usage"]) | set(data["requirement_ids"])
    with open(path, encoding="utf-8") as handle:
        for raw in handle:
            line = raw.split("#")[0].strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 2:
                unknown.append(line)
                continue
            context, element = parts
            if element not in known:
                unknown.append(element)
            elif element in assigned and assigned[element] != context:
                twice.append(element)
            else:
                assigned[element] = context
    shared = []
    for entity, users in data["usage"].items():
        contexts = sorted({assigned[u] for u in users if u in assigned})
        owner = assigned.get(entity)
        others = [c for c in contexts if c != owner]
        if owner and others:
            shared.append({"entity": entity, "owner": owner, "also_used_in": others,
                           "by": [u for u in users if assigned.get(u) in others]})
        elif not owner and len(contexts) > 1:
            shared.append({"entity": entity, "owner": None, "also_used_in": contexts, "by": users})
    crossing = [c for c in data["citations"] if c["from"] in assigned and c["to"] in assigned and assigned[c["from"]] != assigned[c["to"]]]
    journeys = [j for j in data["journeys"] if len({assigned.get(u) for u in j["use_cases"] if u in assigned}) > 1]
    split_reqs = []
    for rid in data["requirement_ids"]:
        contexts = sorted({assigned[u] for u, info in data["use_cases"].items() if rid in info["requirements"] and u in assigned})
        if len(contexts) > 1:
            split_reqs.append({"requirement": rid, "linked_from": contexts, "assigned_to": assigned.get(rid)})
    return {"contexts": sorted(set(assigned.values())), "assigned_twice": sorted(set(twice)), "unknown": unknown,
            "unassigned": sorted(known - set(assigned)), "shared_entities": shared, "crossing_citations": crossing,
            "crossing_journeys": journeys, "requirements_linked_from_several_contexts": split_reqs}


def print_text(data):
    c = data["counts"]
    print("Specification core")
    print("  use cases %(use_cases)d · alternative flows %(alternative_flows)d · business rules %(business_rules)d · "
          "entities %(entities)d · actors %(actors)d · requirements %(requirements)d · journey test cases %(journey_test_cases)d" % c)
    print()
    print("Entity usage")
    for entity, users in sorted(data["usage"].items(), key=lambda kv: (-len(kv[1]), kv[0])):
        print("  %-24s %2d  %s" % (entity, len(users), ", ".join(users) or "—"))
    if data["use_cases_naming_no_entity"]:
        print("  use cases naming no entity: %s" % ", ".join(data["use_cases_naming_no_entity"]))
    print()
    print("Clusters (use cases connected through shared entities): %d" % len(data["clusters"]))
    for index, cluster in enumerate(data["clusters"], 1):
        print("  %d. %s" % (index, ", ".join(cluster["use_cases"])))
        print("     entities: %s" % (", ".join(cluster["entities"]) or "—"))
        print("     actors:   %s" % (", ".join(cluster["actors"]) or "—"))
    print()
    print("Bridges (an entity whose removal separates a cluster; fewest users first, since fewer users mean a smaller contract)")
    for bridge in data["bridges"]:
        print("  %s, named by %d use cases, separates: %s" % (bridge["entity"], bridge["used_by"], " | ".join(", ".join(g) for g in bridge["separates"])))
    if not data["bridges"]:
        print("  none: no single entity holds a cluster together")
    print()
    print("Links between use cases")
    for cite in data["citations"]:
        print("  %s cites %s %s" % (cite["from"], cite["to"], cite["rule"]))
    for journey in data["journeys"]:
        print("  %s chains %s" % (journey["journey"], ", ".join(journey["use_cases"])))
    if not data["citations"] and not data["journeys"]:
        print("  none")
    assignment = data.get("assignment")
    if assignment:
        print()
        print("Proposed assignment: %s" % ", ".join(assignment["contexts"]))
        for label, key in (("assigned to two contexts", "assigned_twice"), ("not in the specification set", "unknown"), ("not assigned", "unassigned")):
            print("  %s: %s" % (label, ", ".join(assignment[key]) or "none"))
        print("  entities used across contexts (each needs a contract):")
        for item in assignment["shared_entities"]:
            owner = item["owner"] or "NO OWNER ASSIGNED"
            print("    %s, owned by %s, used in %s by %s" % (item["entity"], owner, ", ".join(item["also_used_in"]), ", ".join(item["by"])))
        if not assignment["shared_entities"]:
            print("    none")
        print("  citations that cross (must be written with the context name):")
        for cite in assignment["crossing_citations"]:
            print("    %s cites %s %s" % (cite["from"], cite["to"], cite["rule"]))
        if not assignment["crossing_citations"]:
            print("    none")
        print("  journeys that cross (need an owner): %s" % (", ".join(j["journey"] for j in assignment["crossing_journeys"]) or "none"))
        print("  requirements linked from several contexts: %s"
              % (", ".join("%s (%s)" % (r["requirement"], ", ".join(r["linked_from"])) for r in assignment["requirements_linked_from_several_contexts"]) or "none"))
    print()
    print("These numbers describe the set. Whether and where to split is the owner's decision.")


def main(argv):
    parser = argparse.ArgumentParser(description="Measure a specification set and show where it could be cut.")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--assign", help="file with a proposed assignment to check")
    args = parser.parse_args(argv)
    args.docs = args.docs or model.docs_default()
    docs_model = model.Docs(args.docs)
    stop = model.stop_if_old(docs_model)
    if stop:
        return stop
    if not os.path.isdir(args.docs):
        print("no such folder: %s" % args.docs, file=sys.stderr)
        return 2
    try:
        data = measure(model.Docs(args.docs))
        if args.assign:
            data["assignment"] = check_assignment(args.assign, data)
    except (OSError, UnicodeDecodeError) as exc:
        print("cannot read: %s" % exc, file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print_text(data)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
