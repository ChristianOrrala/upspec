#!/usr/bin/env python3
"""Enumerate the start-to-end paths of a BPMN 2.0 process model.

Prints JSON: lanes, activities (with a use case id when the name carries one),
paths and warnings. Each path becomes one journey test case.

Path rules, applied in document order so every run gives the same result:

- Exclusive, inclusive, event-based and complex gateways, and any other node
  with several outgoing flows, are alternatives: each outgoing flow starts its
  own path.
- A parallel gateway runs all branches: they are written one after another in
  the same path, up to the joining parallel gateway.
- A sequence flow is followed at most twice in one path, so a loop yields one
  path without and one with a single repetition.
- A node without outgoing flow ends the path.
- A sub-process is one step; boundary events are not followed. Both are warnings.

The file is data. A file with a document type or entity declaration is refused
before parsing, so no external entity is resolved and no entity can expand.

Exit code 0 on success, 1 when the file is not a usable process model, 2 on
usage errors, 4 when the file was refused.

Usage:
    bpmn_paths.py FILE.bpmn

Requires Python 3.9+, standard library only. Reads the file; writes nothing.
"""
import argparse
import itertools
import json
import re
import sys
import xml.etree.ElementTree as ET

ACTIVITIES = ("task", "userTask", "manualTask", "serviceTask", "sendTask", "receiveTask",
              "scriptTask", "businessRuleTask", "callActivity")
SUBPROCESSES = ("subProcess", "transaction", "adHocSubProcess")
ALTERNATIVE_GATEWAYS = ("exclusiveGateway", "inclusiveGateway", "eventBasedGateway", "complexGateway")
EVENTS = ("startEvent", "endEvent", "intermediateCatchEvent", "intermediateThrowEvent")
NODE_TYPES = ACTIVITIES + SUBPROCESSES + ALTERNATIVE_GATEWAYS + EVENTS + ("parallelGateway", "boundaryEvent")
FORBIDDEN = re.compile(rb"<!\s*(DOCTYPE|ENTITY)", re.IGNORECASE)
UC_ID = re.compile(r"(?<![A-Za-z0-9])(UC-\d{3})(?!\d)")
# Each path becomes one journey document that a person reviews. Beyond a few
# hundred nobody does; the cap also bounds the work on a model with many
# combined decisions. Hitting it is reported as a warning.
MAX_PATHS = 200
# A sequence flow may be followed this many times in one path: once normally,
# once more to show a single repetition of a loop.
MAX_FLOW_USES = 2


class Refused(Exception):
    pass


def local(tag):
    return tag.rsplit("}", 1)[-1]


class Process:
    def __init__(self, element):
        self.id = element.get("id", "")
        self.name = element.get("name") or self.id or "Process"
        self.nodes = {}        # id -> {"type", "name"}
        self.order = []        # node ids in document order
        self.outgoing = {}     # id -> [(flow id, flow name, target id)]
        self.incoming = {}     # id -> count
        self.lane_of = {}
        self.lanes = {}
        self.warnings = []
        for child in element.iter():
            kind = local(child.tag)
            if kind in NODE_TYPES and child.get("id"):
                self.nodes[child.get("id")] = {"type": kind, "name": (child.get("name") or "").strip()}
                self.order.append(child.get("id"))
            elif kind == "lane":
                name = (child.get("name") or child.get("id") or "").strip()
                for ref in child:
                    if local(ref.tag) == "flowNodeRef" and ref.text:
                        self.lane_of[ref.text.strip()] = name
        for child in element.iter():
            if local(child.tag) == "sequenceFlow":
                source, target = child.get("sourceRef"), child.get("targetRef")
                if source in self.nodes and target in self.nodes:
                    self.outgoing.setdefault(source, []).append((child.get("id", ""), (child.get("name") or "").strip(), target))
                    self.incoming[target] = self.incoming.get(target, 0) + 1
                else:
                    self.warnings.append("sequence flow %s refers to a node that does not exist" % child.get("id", "?"))
        for node_id in self.order:
            node = self.nodes[node_id]
            if node["type"] in ACTIVITIES + SUBPROCESSES:
                lane = self.lane_of.get(node_id, self.name)
                self.lanes.setdefault(lane, []).append(node_id)
            if node["type"] in SUBPROCESSES:
                self.warnings.append("sub-process '%s' is treated as one step; its inside is not expanded" % (node["name"] or node_id))
            if node["type"] == "boundaryEvent":
                self.warnings.append("boundary event '%s' is not followed; model the alternative with a gateway" % (node["name"] or node_id))

    def starts(self):
        starts = [n for n in self.order if self.nodes[n]["type"] == "startEvent"]
        if not starts:
            starts = [n for n in self.order if not self.incoming.get(n) and self.nodes[n]["type"] != "boundaryEvent"]
            if starts:
                self.warnings.append("no start event; starting at nodes without incoming flow")
        return starts

    def is_join(self, node_id):
        return self.nodes[node_id]["type"] == "parallelGateway" and self.incoming.get(node_id, 0) > 1

    def step(self, node_id):
        node = self.nodes[node_id]
        if node["type"] in ACTIVITIES + SUBPROCESSES:
            return {"kind": "activity", "id": node_id, "name": node["name"]}
        if node["type"] in EVENTS:
            return {"kind": "event", "id": node_id, "name": node["name"]}
        return None

    def walk(self, node_id, uses, stop_at_join):
        """Return a list of (steps, end node id or join id) alternatives from this node on."""
        results = []
        stack = [(node_id, [], dict(uses))]
        while stack:
            if len(results) >= MAX_PATHS:
                break
            current, steps, used = stack.pop()
            steps = list(steps)
            if stop_at_join and self.is_join(current):
                results.append((steps, current))
                continue
            step = self.step(current)
            if step:
                steps.append(step)
            flows = self.outgoing.get(current, [])
            if not flows:
                results.append((steps, current))
                continue
            kind = self.nodes[current]["type"]
            if kind == "parallelGateway" and len(flows) > 1:
                branches = []
                for flow_id, _, target in flows:
                    branches.append(self.walk(target, used, True))
                joins = {end for branch in branches for _, end in branch if self.is_join(end)}
                if len(joins) != 1:
                    self.warnings.append("parallel gateway '%s' has branches that do not meet at one joining gateway; they are treated as ending" % (self.nodes[current]["name"] or current))
                for combination in itertools.islice(itertools.product(*branches), MAX_PATHS):
                    merged = steps + [s for branch_steps, _ in combination for s in branch_steps]
                    if len(joins) == 1:
                        join = next(iter(joins))
                        for more_steps, end in self.walk_after(join, used, stop_at_join):
                            results.append((merged + more_steps, end))
                    else:
                        results.append((merged, current))
                continue
            for flow_id, flow_name, target in reversed(flows):
                count = used.get(flow_id, 0)
                if count >= MAX_FLOW_USES:
                    continue
                branch_used = dict(used)
                branch_used[flow_id] = count + 1
                branch_steps = list(steps)
                if len(flows) > 1:
                    branch_steps.append({"kind": "decision", "id": current, "name": self.nodes[current]["name"], "flow": flow_name or flow_id})
                stack.append((target, branch_steps, branch_used))
        return results

    def walk_after(self, join_id, uses, stop_at_join):
        """Continue after a joining parallel gateway."""
        results = []
        for flow_id, _, target in self.outgoing.get(join_id, []):
            used = dict(uses)
            used[flow_id] = used.get(flow_id, 0) + 1
            results += self.walk(target, used, stop_at_join)
        return results or [([], join_id)]


def analyze(data):
    if FORBIDDEN.search(data):
        raise Refused("the file has a document type or entity declaration")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError("not well-formed XML: %s" % exc)
    processes = [Process(e) for e in root.iter() if local(e.tag) == "process"]
    processes = [p for p in processes if p.nodes]
    if not processes:
        raise ValueError("no BPMN process with flow nodes found")
    lanes, activities, paths, warnings = {}, [], [], []
    for process in processes:
        warnings += process.warnings
        for lane, ids in process.lanes.items():
            lanes.setdefault(lane, []).extend(ids)
        for node_id in process.order:
            node = process.nodes[node_id]
            if node["type"] in ACTIVITIES + SUBPROCESSES:
                match = UC_ID.search(node["name"])
                activities.append({"id": node_id, "name": node["name"], "type": node["type"],
                                   "lane": process.lane_of.get(node_id, process.name), "ucId": match.group(1) if match else None})
        for start in process.starts():
            for steps, end in process.walk(start, {}, False):
                if len(paths) >= MAX_PATHS:
                    break
                paths.append({"number": len(paths) + 1, "process": process.name, "steps": steps,
                              "activities": [s["id"] for s in steps if s["kind"] == "activity"],
                              "decisions": ["%s: %s" % (s["name"] or s["id"], s["flow"]) for s in steps if s["kind"] == "decision"],
                              "end": process.nodes[end]["name"] or end})
        warnings += [w for w in process.warnings if w not in warnings]
    if len(paths) >= MAX_PATHS:
        warnings.append("more than %d paths; only the first %d are listed. Split the process or choose the paths that matter" % (MAX_PATHS, MAX_PATHS))
    if not paths:
        raise ValueError("no path from a start to an end was found")
    return {"lanes": lanes, "activities": activities, "paths": paths, "warnings": warnings}


def main(argv):
    parser = argparse.ArgumentParser(description="Enumerate the paths of a BPMN 2.0 process model.")
    parser.add_argument("file")
    args = parser.parse_args(argv)
    try:
        with open(args.file, "rb") as handle:
            data = handle.read()
    except OSError as exc:
        print("cannot read %s: %s" % (args.file, exc), file=sys.stderr)
        return 2
    try:
        result = analyze(data)
    except Refused as exc:
        print("refused: %s" % exc, file=sys.stderr)
        return 4
    except ValueError as exc:
        print("not a usable process model: %s" % exc, file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
