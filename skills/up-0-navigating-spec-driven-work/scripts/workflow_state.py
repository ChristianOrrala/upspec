#!/usr/bin/env python3
"""Read the state of a specification-driven repository and name the first step that applies.

State comes from the files, never from memory:
  - the profile and skipped artifacts recorded in the guideline file (AGENTS.md or CLAUDE.md);
  - which artifacts of the chain exist (vision, catalog, entity model, diagram);
  - every use case with its Status, including Draft stubs awaiting their body;
  - a recovery in progress: use cases recovered from code (rows in docs/recovery/ledger.md)
    whose specification is still Draft, waiting for the baseline review;
  - invalid identifiers or Status values in specification files;
  - journey test cases, and whether the repository holds code.
  - with the A-files (ACTIVE.md with a hot zone): the current work, what blocks it and
    what waits on the owner, AHEAD's Next up, the abilities and the use cases their
    Specs lines name. The step for the current work comes before the others; a use
    case in progress that the current work does not name, and an ability whose
    status disagrees with its use cases, are listed.
  - the alignment backlog of a recovery (docs/recovery/change-log.md): entries decided
    later or in change are open; aligned closes only when the shared closure check
    finds no errors in its audit reports, otherwise it stays open with warnings;
    dropped is closed and undecided is counted. An entry in change whose use cases
    are all Tested or Done gets a hint that its audit report can close it. With the
    A-files, a later entry without an AHEAD item, an AHEAD item that does not exist and
    a done ability with open entries are warned. The count never changes the next step.

The decision rows are tried top to bottom; the first that matches is the next
step. Every use case also gets its own next step, so work on another use case
can go on in parallel.

Step codes: SETUP, RECOVER, BASELINE_REVIEW, VISION, REQUIREMENTS, ENTITY_MODEL, DIAGRAM,
FIX, TEST, IMPLEMENT, APPROVE, REVIEW, SPECIFY, MAP, JOURNEY, BUSINESS_REVIEW, IDLE.

Exit code 0, 2 on usage errors.

Usage:
    workflow_state.py [--docs DIR] [--format text|json]

Requires Python 3.9+, standard library only. Reads files as data; writes nothing.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import use_case_map
import spec_model as model  # noqa: E402  (local module, same folder)

# the release these copies belong to; hook_gate.py refuses siblings of another release
UPSPEC_VERSION = "1.1.0"

PLACEHOLDER = re.compile(r"\[[^\]\n]+\](?!\()")
SOURCE_SUFFIXES = (".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".java", ".kt", ".kts", ".go", ".rb", ".php",
                   ".cs", ".rs", ".swift", ".scala", ".c", ".h", ".cc", ".cpp", ".hpp", ".sql", ".vue", ".svelte",
                   ".ex", ".exs", ".dart", ".groovy")
# Counting stops here: the question is whether there is a code base, not how large it is.
CODE_COUNT_CAP = 50
# A use case in these Status values has been built and is waiting for tests or for the business: work in progress.
IN_PROGRESS = ("Implemented", "Tested")
# Status values at which a use case can be audited for alignment: the hint names the report that would close it.
READY = ("Tested", "Done")
# Inspect both installation sets without depending on the plugin-only installed_copies module.
INSTALLED_SCRIPTS = ("hook_gate.py", "workflow_state.py", "validate_use_case.py", "finish_change.py",
                     "scope_audit.py", "uc_change_list.py", "unrecorded_changes.py", "spec_model.py",
                     "use_case_map.py", "change_view.py", "hook_profiles.py", "spec_lint.py", "spec_first_guard.py")
# Read a literal release line as data, using the same format as hook_gate and the release checks.
VERSION_LINE = re.compile(r'^UPSPEC_VERSION = "(\d+\.\d+\.\d+)"$', re.M)

# Status -> (step code, who or which skill acts, what happens)
PER_STATUS = {
    "Draft": ("REVIEW", "up-6-reviewing-specifications", "validator clean, then an independent review; Status becomes Reviewed"),
    "Reviewed": ("APPROVE", "a person", "a named person signs the specification off; Status becomes Approved"),
    "Approved": ("IMPLEMENT", "up-7-implementing-use-cases", "build the slice; Status becomes Implemented when the code is merged with its markers"),
    "Implemented": ("TEST", "up-8-deriving-use-case-tests", "tests for every flow and rule of the built slice, then up-9-auditing-spec-coverage; Status becomes Tested when all pass"),
    "Tested": ("BUSINESS_REVIEW", "a person", "the business accepts the behavior; Status becomes Done"),
}
SKILLS = {
    "SETUP": "up-1-bootstrapping-spec-driven-projects", "VISION": "up-1-bootstrapping-spec-driven-projects",
    "RECOVER": "up-recovering-specs-from-code", "REQUIREMENTS": "up-2-cataloging-requirements",
    "BASELINE_REVIEW": "up-6-reviewing-specifications, then the owner",
    "ENTITY_MODEL": "up-3-modeling-domain-entities", "DIAGRAM": "up-4-mapping-use-cases", "FIX": "up-6-reviewing-specifications",
    "FIX_FORMAT": "up-6-reviewing-specifications",
    "SPECIFY": "up-5-writing-use-case-specs", "MAP": "up-4-mapping-use-cases", "JOURNEY": "up-writing-journey-test-cases",
    "IDLE": "up-triaging-change-requests",
}


def update_notice(root: str) -> "str | None":
    """Report older installed copies only when this reader runs from the plugin."""
    folder = os.path.join(root, "tools", "specs")
    if (not os.path.isdir(folder) or
            os.path.realpath(__file__) == os.path.realpath(os.path.join(folder, "workflow_state.py"))):
        return None
    versions, unmarked = [], False
    for name in INSTALLED_SCRIPTS:
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as handle:
                match = VERSION_LINE.search(handle.read())
        except (OSError, UnicodeError):
            # A notice is advisory; an unreadable version must not stop the state report.
            match = None
        if match:
            versions.append(tuple(int(part) for part in match.group(1).split(".")))
        else:
            unmarked = True
    if not unmarked and (not versions or min(versions) >= tuple(int(p) for p in UPSPEC_VERSION.split("."))):
        return None
    installed = "before 1.1.0" if unmarked else ".".join(str(p) for p in min(versions))
    return ("Installed upspec scripts in tools/specs/ are %s; "
            "this plugin is %s: run scaffold_docs.py --update to see what changes." % (installed, UPSPEC_VERSION))


def skill_for_artifact(path):
    path = path.replace("\\", "/")
    if any("/" + folder + "/" in "/" + path for folder in ("use_cases", "use-cases")):
        return "up-5-writing-use-case-specs"
    if path.endswith(("use_cases.md", "use-cases.md")):
        return "up-4-mapping-use-cases"
    if "requirements" in path:
        return "up-2-cataloging-requirements"
    if "entity_model" in path or "entity-model" in path:
        return "up-3-modeling-domain-entities"
    if any("/" + folder + "/" in "/" + path for folder in ("test_cases", "test-cases")):
        return "up-writing-journey-test-cases"
    if "change-records" in path or "change_records" in path:
        return "up-triaging-change-requests"
    return "up-6-reviewing-specifications"


def recovered_ids(docs):
    """Use case ids that have a row in the recovery ledger: these were recovered from code."""
    if not docs or not docs.recovery_dir:
        return set()
    path = os.path.join(docs.recovery_dir, "ledger.md")
    if not os.path.isfile(path):
        return set()
    ids = set()
    for table in model.read_tables(model.read_lines(path)):
        if table["header"] and table["header"][0].strip().lower() == "element":
            for _, row, _ in table["rows"]:
                match = re.match(r"^`?(UC-\d{3})\b", row.get(table["header"][0], "").strip())
                if match:
                    ids.add(match.group(1))
    return ids


def alignment_view(root, docs, use_cases):
    """The alignment backlog of a recovery, or None when its change log has no entry."""
    if not docs or not docs.recovery_dir:
        return None
    entries = model.parse_change_log(os.path.join(docs.recovery_dir, "change-log.md"))
    if not entries:
        return None
    status = {u["id"]: u["status"] for u in use_cases}
    counts = {"later": 0, "in_change": 0, "aligned": 0, "dropped": 0, "undecided": 0}
    open_entries, ready, warnings = [], [], []
    for entry in entries:
        state = entry["state"]
        errors = [message for severity, _, message in model.closure_problems(root, entry) if severity == "error"]
        warnings.extend("change log #%d is aligned, but %s; it stays open" % (entry["number"], message)
                        for message in errors)
        if state in counts and not errors:
            counts[state] += 1
        if state not in ("later", "in_change") and not errors:
            continue
        record = entry["paths"][0] if state == "in_change" and entry["paths"] else None
        named = model.RE_UC_ID.search(os.path.basename(record)) if record else None
        ids = unique(([named.group(0)] if named else []) + entry["use_cases"])
        open_entries.append({"number": entry["number"], "state": state, "use_cases": ids, "record": record, "ahead": entry["ahead"]})
        if state == "in_change" and ids and all(status.get(uc) in READY for uc in ids):
            ready.append("change log #%d: %s; its audit report closes it (aligned: <report>)"
                         % (entry["number"], ", ".join("%s is %s" % (uc, status[uc]) for uc in ids)))
    return dict(counts, open=len(open_entries), entries=open_entries, ready=ready, warnings=warnings,
                ahead_items=unique([item for e in open_entries for item in e["ahead"]]), abilities=[])


def alignment_line(alignment):
    text = ("Alignment: %(open)d open (%(later)d later, %(in_change)d in change), %(aligned)d aligned, "
            "%(dropped)d dropped, %(undecided)d undecided" % alignment)
    if alignment["ahead_items"]:
        text += "; AHEAD %s" % ", ".join(alignment["ahead_items"])
    if alignment["abilities"]:
        text += "; abilities %s" % ", ".join(alignment["abilities"])
    return text


def count_code(root, docs_dir):
    docs_abs = os.path.abspath(docs_dir)
    count = 0
    for path in model.iter_source_files(root, SOURCE_SUFFIXES):
        full = os.path.abspath(path)
        if full.startswith(docs_abs + os.sep) or (os.sep + os.path.join("tools", "specs") + os.sep) in full:
            continue
        count += 1
        if count >= CODE_COUNT_CAP:
            break
    return count


def unique(items):
    seen = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def focus_of(tracking):
    """The use cases the current work names (directly or through its abilities), else those of Next up's first item."""
    abilities = tracking["abilities"]
    current = tracking["current_work"]
    if tracking["active_home"]:
        return [], None                    # the current work is kept elsewhere: no guess from AHEAD
    if current:
        ids = model.RE_UC_ID.findall(current)
        for ability in model.RE_AB_ID.findall(current):
            ids += abilities.get(ability, {}).get("specs", [])
        return unique(ids), "ACTIVE.md current work"
    for item in tracking["next_up"][:1]:
        ids = [uc for ability in tracking["items"].get(item, []) for uc in abilities.get(ability, {}).get("specs", [])]
        if ids:
            return unique(ids), "AHEAD.md Next up (%s)" % item
    return [], None


def tracking_view(root, use_cases, alignment=None):
    """What the A-files add to the state, or None when the project does not use them."""
    tracking = model.read_tracking(root)
    if tracking is None:
        return None
    known = {u["id"]: u for u in use_cases}
    warnings, notes, named_by = [], [], {}
    for ability, entry in sorted(tracking["abilities"].items()):
        for uc_id in entry["specs"]:
            named_by.setdefault(uc_id, []).append(ability)
            if uc_id not in known:
                warnings.append("%s names %s in its Specs line, and no such use case exists" % (ability, uc_id))
        named = [known[u] for u in entry["specs"] if u in known]
        if entry["status"] == "done":
            behind = ["%s is %s" % (u["id"], u["status"]) for u in named if u["status"] != "Done"]
            if behind:
                warnings.append("%s is done, but %s" % (ability, ", ".join(behind)))
        if entry["status"] == "planned":
            ahead = ["%s is %s" % (u["id"], u["status"]) for u in named if u["status"] in ("Implemented", "Tested", "Done")]
            if ahead:
                warnings.append("%s is planned, but %s" % (ability, ", ".join(ahead)))
    if alignment:
        open_on = {}
        for item in alignment["entries"]:
            for uc_id in item["use_cases"]:
                open_on.setdefault(uc_id, []).append(item["number"])
        alignment["abilities"] = sorted({ab for uc_id in open_on for ab in named_by.get(uc_id, [])})
        for ability, entry in sorted(tracking["abilities"].items()):
            left = ["#%d on %s" % (n, uc_id) for uc_id in entry["specs"] for n in open_on.get(uc_id, [])]
            if entry["status"] == "done" and left:
                warnings.append("%s is done, but change log %s %s still open" % (ability, ", ".join(left), "is" if len(left) == 1 else "are"))
        if not tracking["ahead_home"]:
            for item in alignment["entries"]:
                if item["state"] == "later" and not item["ahead"]:
                    warnings.append("change log #%d is later and names no AHEAD item: draft its item (the hand-off at the end of the baseline review)" % item["number"])
                for ahead in item["ahead"]:
                    if ahead not in tracking["items"]:
                        warnings.append("change log #%d names %s, which AHEAD.md does not list" % (item["number"], ahead))
    if not tracking["abilities_home"]:
        unnamed = [u["id"] for u in use_cases if u["id"] not in named_by and u["status"] != "Obsolete"]
        if unnamed:
            notes.append("named by no ability: %s" % ", ".join(unnamed))
    if tracking["abilities_home"]:
        notes.append("abilities are kept in %s: their Specs lines and status checks do not apply" % tracking["abilities_home"])
    if tracking["active_home"]:
        notes.append("the current work is kept in %s: read it there; no mismatch is reported" % tracking["active_home"])
    if tracking["ahead_home"]:
        notes.append("what is ahead is kept in %s" % tracking["ahead_home"])
    focus, focus_from = focus_of(tracking)
    if focus and all(known.get(u, {}).get("status") == "Done" for u in focus):
        if focus_from == "ACTIVE.md current work":
            notes.append("every use case of the current work is Done: close it out in ACTIVE.md and ABILITIES.md")
        else:
            notes.append("every use case of %s is Done: the item can be closed in AHEAD.md" % tracking["next_up"][0])
    if not focus and not tracking["current_work"] and not tracking["active_home"] and tracking["next_up"]:
        notes.append("AHEAD.md's Next up starts with %s, which names no ability with a Specs line" % tracking["next_up"][0])
    mentioned = focus if focus_from == "ACTIVE.md current work" else []
    mismatches = [] if tracking["active_home"] else [
        "%s is %s and the current work does not name it" % (u["id"], u["status"])
        for u in use_cases if u["status"] in IN_PROGRESS and u["id"] not in mentioned]
    return {"current_work": tracking["current_work"], "blocked_by": tracking["blocked_by"],
            "waiting_on_owner": tracking["waiting_on_owner"], "focus": focus, "focus_from": focus_from,
            "mismatches": mismatches, "warnings": warnings, "notes": notes}


def collect(docs_dir):
    root = model.project_root(docs_dir)
    notice = update_notice(root)
    docs = model.Docs(docs_dir)
    earlier = model.old_formats(docs)
    if earlier:
        return {"docs": docs_dir, "notice": notice, "migration": {"code": "MIGRATE", "skill": "up-migrating-spec-formats",
                                               "why": "%d files in earlier formats" % len(earlier)}}
    state = {"docs": docs_dir, "docs_exists": os.path.isdir(docs_dir), "notice": notice}
    guideline, profile, skipped = model.read_rules_block(root)
    state["guideline"] = {"file": guideline, "profile": profile,
                          "skipped": [word for word in ("requirements", "entity model", "overview", "diagram") if word in skipped]}
    docs = model.Docs(docs_dir) if state["docs_exists"] else None
    artifacts = {}
    for key, path in (("vision", docs and docs.vision), ("requirements", docs and docs.requirements),
                      ("entity_model", docs and docs.entity_model), ("diagram", docs and docs.overview)):
        artifacts[key] = {"path": os.path.relpath(path, root) if path else None, "present": bool(path)}
    if docs and docs.vision:
        text = re.sub(r"<!--.*?-->", "", "\n".join(model.read_lines(docs.vision)), flags=re.DOTALL)
        artifacts["vision"]["placeholders"] = len(PLACEHOLDER.findall(text))
    artifacts["diagram"]["current"] = bool(docs and use_case_map.current(docs))
    state["artifacts"] = artifacts

    use_cases, mismatches = [], []
    specs = model.load_use_cases(docs) if docs else []
    seen = {}
    for uc in specs:
        rel = os.path.relpath(uc.path, root)
        if not uc.id:
            mismatches.append("%s has no Use Case ID" % rel)
            continue
        if uc.id in seen:
            mismatches.append("%s is used by %s and %s" % (uc.id, seen[uc.id], rel))
            continue
        seen[uc.id] = rel
        status = uc.status
        if status not in model.UC_STATUSES:
            mismatches.append("%s has Status '%s', which is not a Status" % (uc.id, status))
        step = (("WRITE", "up-5-writing-use-case-specs", "write the stub's specification")
                if uc.is_stub else PER_STATUS.get(status))
        use_cases.append({"id": uc.id, "name": uc.name, "status": status, "file": rel,
                          "next": step[0] if step else None, "by": step[1] if step else None, "what": step[2] if step else None})
    use_cases.sort(key=lambda u: u["id"])
    state["use_cases"] = use_cases
    recovered = recovered_ids(docs)
    state["recovery"] = {"ledger": bool(recovered),
                         "draft": [u["id"] for u in use_cases if u["id"] in recovered and u["status"] == "Draft"]}
    state["mismatches"] = mismatches

    unrealized = []
    if docs and docs.requirements:
        linked = {rid for uc in specs for rid in uc.requirement_ids}
        for req in model.parse_requirements(docs.requirements)[0]:
            if req.kind == "FR" and req.status not in model.REQ_SCOPE and req.id not in linked:
                unrealized.append(req.id)
    state["requirements_without_use_case"] = unrealized
    state["journey_test_cases"] = len(docs.test_case_files()) if docs else 0
    state["code_files"] = count_code(root, docs_dir)
    state["code_files_capped"] = state["code_files"] >= CODE_COUNT_CAP
    findings = model.format_findings(docs) if docs else []
    state["format_findings"] = [{"path": os.path.relpath(p, root), "line": l, "code": c, "message": m}
                                 for p, l, c, m in findings]
    state["alignment"] = alignment_view(root, docs, use_cases)
    state["tracking"] = tracking_view(root, use_cases, state["alignment"])
    return state


def decide(state):
    """First matching row wins. Returns the next step as a dict."""
    if "migration" in state:
        return state["migration"]
    art, guide, ucs = state["artifacts"], state["guideline"], state["use_cases"]
    skipped = guide["skipped"]
    specified = [u for u in ucs if u["file"]]
    chain_started = any(art[k]["present"] for k in ("requirements", "entity_model")) or bool(specified)

    def step(code, target, reason, by=None, what=None):
        return {"code": code, "target": target, "by": by or SKILLS.get(code), "reason": reason, "what": what}

    def first(code):
        return next((u for u in ucs if u["next"] == code), None)

    def where(name):
        """A file of the specification folder, written as the user passed or recorded the folder."""
        return "%s/%s" % (state["docs"].replace(os.sep, "/").rstrip("/"), name)

    findings = state.get("format_findings", [])
    if findings:
        finding = findings[0]
        skill = skill_for_artifact(finding["path"])
        names_and_codes = ", ".join(sorted({"%s (%s)" % (f["path"], f["code"]) for f in findings}))
        return step("FIX_FORMAT", finding["path"],
                    "%d format finding(s): %s" % (len(findings), names_and_codes),
                    by=skill, what="repair the reported format findings using %s" % skill)

    if not guide["file"] and not art["vision"]["present"] and not chain_started:
        return step("SETUP", None, "no rules block in a guideline file, no vision and no specifications")
    if not chain_started and state["code_files"]:
        return step("RECOVER", None, "the repository holds code (%s%d source files) and no specifications"
                    % ("at least " if state["code_files_capped"] else "", state["code_files"]),
                    what="if that code is behavior to keep, recover its specifications; if it is only a fresh scaffold, continue with the vision")
    draft = state["recovery"]["draft"]
    if draft:
        return step("BASELINE_REVIEW", draft[0], "%d use case(s) recovered from code are still Draft: %s" % (len(draft), ", ".join(draft)),
                    what="the baseline review (docs/recovery/baseline-review.md): an independent review of each draft, then the owner "
                         "answers the system and business questions; open items go to the change log. The vision and catalog can follow it")
    if not art["vision"]["present"]:
        return step("VISION", where("vision.md"), "the vision is missing; a person writes it", what="scaffold the skeleton, then the owner writes it")
    if art["vision"].get("placeholders"):
        return step("VISION", art["vision"]["path"], "the vision still holds %d placeholder(s); a person writes it" % art["vision"]["placeholders"],
                    what="the owner fills it in; then the readiness check")
    if not art["requirements"]["present"] and "requirements" not in skipped:
        return step("REQUIREMENTS", where("requirements.md"), "the requirements catalog is missing and not recorded as skipped")
    if not art["entity_model"]["present"] and "entity model" not in skipped:
        return step("ENTITY_MODEL", where("entity_model.md"), "the entity model is missing and not recorded as skipped; it comes before any use case")
    if (not art["diagram"]["present"] or not art["diagram"]["current"]) and not any(k in skipped for k in ("diagram", "overview")):
        return step("DIAGRAM", where("use_cases.md"), "the use case overview is missing or stale and not recorded as skipped")
    if state["mismatches"]:
        return step("FIX", None, "specification files need repair: %s" % state["mismatches"][0], what="run the specification lint and repair what it reports")
    tracking = state.get("tracking")
    if tracking and tracking["focus"]:
        focus = [u for u in ucs if u["id"] in tracking["focus"]]
        for code in ("TEST", "IMPLEMENT", "APPROVE", "WRITE", "REVIEW", "SPECIFY", "BUSINESS_REVIEW"):
            uc = next((u for u in focus if u["next"] == code), None)
            if uc:
                return step(code, uc["id"], "%s %s has Status %s; %s names it" % (uc["id"], uc["name"], uc["status"], tracking["focus_from"]),
                            by=uc["by"], what=uc["what"])
    for code in ("TEST", "IMPLEMENT", "APPROVE", "WRITE", "REVIEW", "SPECIFY"):
        uc = first(code)
        if uc:
            return step(code, uc["id"], "%s %s has Status %s" % (uc["id"], uc["name"], uc["status"]), by=uc["by"], what=uc["what"])
    if not specified:
        return step("SPECIFY", None, "no use case is specified yet", what="specify the first use case: one behavior that is contested or unclear today")
    if state["requirements_without_use_case"]:
        return step("MAP", state["requirements_without_use_case"][0],
                    "no use case realizes %s" % ", ".join(state["requirements_without_use_case"]), what="add the missing use case file and regenerate the overview, or defer the requirement")
    tested = [u for u in ucs if u["status"] in ("Tested", "Done")]
    if len(tested) >= 2 and not state["journey_test_cases"]:
        return step("JOURNEY", None, "%d use cases are Tested or Done and no journey test case chains them" % len(tested),
                    what="write a journey test case where use cases hand state to each other")
    uc = first("BUSINESS_REVIEW")
    if uc:
        return step("BUSINESS_REVIEW", uc["id"], "%s %s has Status Tested" % (uc["id"], uc["name"]), by=uc["by"], what=uc["what"])
    return step("IDLE", None, "every use case is Done", what="nothing is in flight; the next request is classified as a change")


def print_text(state):
    if "migration" in state:
        nxt = state["migration"]
        print("Next step: %s" % nxt["code"])
        if state.get("notice"):
            print(state["notice"])
        print("  by: %s\n  reason: %s" % (nxt["skill"], nxt["why"]))
        return
    guide = state["guideline"]
    print("Profile: %s%s" % (guide["profile"] or "not recorded", " (%s)" % guide["file"] if guide["file"] else " (no rules block found in AGENTS.md or CLAUDE.md)"))
    if state.get("notice"):
        print(state["notice"])
    if guide["skipped"]:
        print("Skipped: %s" % ", ".join(guide["skipped"]))
    print("Artifacts")
    for key, label in (("vision", "vision"), ("requirements", "requirements catalog"), ("entity_model", "entity model"), ("diagram", "use case overview")):
        item = state["artifacts"][key]
        note = item["path"] if item["present"] else "missing"
        if key == "vision" and item.get("placeholders"):
            note += ", %d placeholder(s) left" % item["placeholders"]
        print("  %-22s %s" % (label, note))
    print("  %-22s %d" % ("journey test cases", state["journey_test_cases"]))
    print("  %-22s %s%d" % ("source files", "at least " if state["code_files_capped"] else "", state["code_files"]))
    print("Use cases")
    for uc in state["use_cases"]:
        print("  %s  %-32s %-13s %s" % (uc["id"], uc["name"][:32], uc["status"], "next: %s" % uc["next"] if uc["next"] else "—"))
    if not state["use_cases"]:
        print("  none")
    if state["mismatches"]:
        print("Mismatches")
        for item in state["mismatches"]:
            print("  %s" % item)
    if state.get("format_findings"):
        print("Format findings")
        for f in state["format_findings"]:
            print("  %s:%d: %s: %s" % (f["path"], f["line"], f["code"], f["message"]))
    nxt = state["next"]
    print()
    print("Next step: %s%s" % (nxt["code"], " " + nxt["target"] if nxt["target"] else ""))
    print("  by:     %s" % nxt["by"])
    print("  reason: %s" % nxt["reason"])
    if nxt["what"]:
        print("  what:   %s" % nxt["what"])

    alignment = state.get("alignment")
    if alignment and any(alignment[key] for key in ("open", "aligned", "dropped", "undecided")):
        print()
        print(alignment_line(alignment))
        for warning in alignment["warnings"]:
            print("  warning: %s" % warning)
        for hint in alignment["ready"]:
            print("  ready: %s" % hint)

    tracking = state.get("tracking")
    if tracking:
        print()
        print("Tracking (A-files)")
        print("  current work:     %s%s" % (tracking["current_work"] or "none",
                                            "  (focus: %s, from %s)" % (", ".join(tracking["focus"]), tracking["focus_from"]) if tracking["focus"] else ""))
        if tracking["blocked_by"]:
            print("  blocked by:       %s" % tracking["blocked_by"])
        if tracking["waiting_on_owner"]:
            print("  waiting on owner: %s" % tracking["waiting_on_owner"])
        for line in tracking["mismatches"]:
            print("  mismatch:         %s" % line)
        for line in tracking["warnings"]:
            print("  warning:          %s" % line)
        for line in tracking["notes"]:
            print("  note:             %s" % line)


def main(argv):
    parser = argparse.ArgumentParser(description="Read the state of a specification-driven repository.")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    args.docs = args.docs or model.docs_default()
    if os.path.exists(args.docs) and not os.path.isdir(args.docs):
        print("not a folder: %s" % args.docs, file=sys.stderr)
        return 2
    try:
        state = collect(args.docs)
    except (OSError, UnicodeDecodeError) as exc:
        print("cannot read the specifications: %s" % exc, file=sys.stderr)
        return 2
    state["next"] = decide(state)
    if args.format == "json":
        print(json.dumps(state, indent=2, ensure_ascii=False))
    else:
        print_text(state)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
