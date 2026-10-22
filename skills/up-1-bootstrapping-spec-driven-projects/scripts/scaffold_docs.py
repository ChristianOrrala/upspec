#!/usr/bin/env python3
"""Set a repository up for specification-first work: plan first, apply on request, decide customized copies.

Both profiles:
  docs/vision.md                       skeleton for a person to fill in
  docs/use_cases/, docs/test_cases/    empty folders, kept with a .gitkeep
  the guideline file                   gets the rules block appended once (created if absent)

Team profile, in addition:
  tools/specs/                         copies of the check scripts, so the pipeline needs nothing installed
  the pull request template and the pipeline job of the chosen host

With --hooks, either profile:
  tools/specs/                         the gate of the agent hooks (hook_gate.py) and the scripts it
                                       calls; --tool also plans that tool's project wiring

When the project tracks its work in the A-files (ACTIVE.md with a hot zone), the
plan also joins them: the rules section is named in the hot zone of AGENTS.md,
the keep-in-step list gains two rows, and ATLAS.md gains a row for the
specifications. Specifications found outside the specification folder (this
method's use cases elsewhere, Spec Kit's specs/, Kiro's .kiro/specs/,
OpenSpec's openspec/) are named in a note; nothing is moved.

Without --apply nothing is written: the plan is printed. Setup keeps existing
documents and appends the rules block once. It proposes a missing integration
branch line and joins the A-files once. --update refreshes installed scripts;
--hooks on an existing setup uses the same classification and update plan.
Untouched copies are replaced. Customized copies show a diff and need an
explicit --replace NAME or --keep NAME decision before any file is written.
The bundle records package baselines and fingerprints of kept customizations.
The integration line comes from detection alone. Local overrides stay local,
and --no-integration-line declines that line while accepting script updates.

When docs/vision.md exists, the sections that are missing or still hold
placeholder text are listed.

When the project already has a product document (PRODUCT.md, VISION.md, a PRD,
docs/product.md ...), the new vision does not restate it: its Mission and Target
Users sections point to that document. A project glossary found on the way is
named in the plan, so that the entity model takes its terms.

Exit code 0, 1 when --apply meets undecided copies, 2 on usage errors.

Usage:
    scaffold_docs.py [--root DIR] [--profile solo|team] [--host github|gitlab|none]
                     [--guideline FILE] [--specs-folder DIR] [--skip requirements|overview|entity-model ...] [--hooks]
                     [--update] [--replace NAME ...] [--keep NAME ...] [--no-integration-line] [--apply]

--hooks --tool claude|codex|antigravity|kiro generates wiring from the tool's
profile. Unrecorded direct hooks and legacy adapters need a decision per
moment: --replace wiring:<moment> or --keep wiring:<moment>. Repeat --reason
TEXT in the order of the kept wiring moments to record why they were kept.
Unreadable JSON or an undecided moment prevents every write in the plan.

The rules block goes into AGENTS.md when it stands alone or is imported by
CLAUDE.md, otherwise into an existing CLAUDE.md; --guideline names another file.

--skip records, for the solo profile, an artifact of the chain that the owner
decided to leave out, as a line in the rules block that other skills read.

--specs-folder keeps the specifications in another folder inside the project
(default: the folder the rules block records, else docs). A folder other than
docs is recorded in the rules block as **Specs folder:**, where every script
of the skills reads it, and the rules block names it in its paths. When a
guideline file already holds the rules block, --specs-folder must name the
folder that block records, and setup refuses to write a second block into
another guideline file (exit 2, nothing written).

Requires Python 3.9+, standard library only.
"""
import argparse
from collections import Counter
import difflib
import json
import os
import re
import shutil
import shlex
from pathlib import Path
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model  # noqa: E402  (local module, same folder)
import change_view  # noqa: E402
import installed_copies  # noqa: E402
import hook_profiles  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(os.path.dirname(HERE), "templates")
RULES_HEADING = "## Working from specifications"
CHECK_SCRIPTS = ("spec_model.py", "validate_use_case.py", "spec_lint.py", "use_case_map.py", "spec_first_guard.py")
# The gate of the agent hooks and every script it calls; copied together so that the gate runs from the project.
HOOK_SCRIPTS = ("hook_gate.py", "workflow_state.py", "validate_use_case.py", "finish_change.py", "scope_audit.py",
                "uc_change_list.py", "unrecorded_changes.py", "spec_model.py", "use_case_map.py", "change_view.py", "hook_profiles.py")
VISION_SECTIONS = ("Mission", "Target Users", "Goals", "Core Terms", "In Scope", "Out of Scope", "Neighboring Systems",
                   "Constraints", "Success Measures")
# What a solo project may leave out, and the words recorded for it in the rules block.
SKIPPABLE = {"requirements": "requirements catalog", "overview": "use case overview", "diagram": "use case overview", "entity-model": "entity model"}
PLACEHOLDER = re.compile(r"\[[^\]\n]+\](?!\()")       # [text] that is not a Markdown link
# Files that already say what a product is for and who uses it, in the order they are looked for.
PRODUCT_DOCS = ("PRODUCT.md", "VISION.md", "PRD.md", "docs/PRODUCT.md", "docs/product.md", "docs/prd.md",
                "docs/product/README.md", "docs/product/index.md")
GLOSSARIES = ("GLOSSARY.md", "docs/glossary.md", "docs/GLOSSARY.md", "docs/reference/glossary.md")
HOST_FILES = {
    "github": {"pull-request.md": ".github/pull_request_template.md", "ci-github.yml": ".github/workflows/specifications.yml"},
    "gitlab": {"pull-request.md": ".gitlab/merge_request_templates/Default.md"},
    "none": {},
}
MARKER = "<!-- hot zone ends -->"
# The two keep-in-step rows of the pairing contract (P1), worded as the A-files' pairing reference words them.
KEEP_ROWS = ("- `ABILITIES.md` when a use case changes Status: the ability whose `Specs` line names it follows it;",
             "- `ABILITIES.md` when a use case is mapped: it joins an ability's `Specs` line;")
# Folders where other methods keep their specifications: named in a note, never moved by the scaffold.
OTHER_SPECS = (("specs", "Spec Kit or another method"), (".kiro/specs", "Kiro"), ("openspec", "OpenSpec"))
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "target", "__pycache__"}
# The A-files' cap for a hot zone: a join that would pass it stops with a note (their check would refuse it).
HOT_CAP = 100
# Event names are the tool contracts in research 12, including Kiro's file variant.
WIRING_MOMENTS = {"SessionStart": "session-start", "PostToolUse": "after-edit",
                  "PostFileSave": "after-edit", "PostFileCreate": "after-edit", "Stop": "before-stop"}
# These names preserve the established named groups and Kiro hook names.
WIRING_NAMES = {"session-start": "up-session-state", "after-edit": "up-specification-check",
                "before-stop": "up-finish-check"}
# Why a moment is not generated: trial 04 saw only what reached the agent, and its runs were headless.
NOT_GENERATED_WHY = {"antigravity": "nothing reached the agent on Antigravity CLI 1.4.4; per the tool's 1.4.3 "
                                    "changelog the failure is only logged"}
# A direct gate or one of the released adapters covers a moment already.
WIRING_CALL = re.compile(r"(?:^|[\s\"'/])(?:tools/specs/hook_gate\.py|up_hook\.py|\.(?:codex|agents|kiro)/up_hook\.py)(?=$|[\s\"';])")


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def rules_block(profile, skipped=(), folder="docs", branch=None):
    """The rules block with the profile filled in, and the artifacts a solo project decided to leave out."""
    text = read(os.path.join(TEMPLATES, "guideline-rules.md"))
    line = "**Profile:** %s" % profile
    if skipped:
        line += "  \n**Skipped:** %s" % ", ".join(skipped)
    if folder != "docs" or branch:
        line += "  \n**Specs folder:** %s" % folder
    if branch:
        line += "  \n**Integration branch:** %s" % branch
    if folder != "docs":
        for name in ("", "use_cases/", "requirements.md", "entity_model.md"):
            text = text.replace("`docs/%s`" % name, "`%s/%s`" % (folder, name))
    return text.replace("**Profile:** [solo | team]", line).rstrip("\n") + "\n"


def pick_guideline(root, wanted):
    """Choose the file the rules block goes into, and a note when another guideline file will not carry it.

    An agent that finds a CLAUDE.md reads it instead of AGENTS.md, unless the CLAUDE.md imports AGENTS.md.
    So: AGENTS.md when it is alone or imported; otherwise the existing CLAUDE.md; AGENTS.md for a fresh project.
    """
    agents = os.path.isfile(os.path.join(root, "AGENTS.md"))
    claude = os.path.isfile(os.path.join(root, "CLAUDE.md"))
    if wanted:
        return wanted, None
    if claude:
        imports = agents and re.search(r"(?m)^\s*(?:[-*]\s*)?@AGENTS\.md\b", read(os.path.join(root, "CLAUDE.md")))
        if imports:
            return "AGENTS.md", None
        note = "AGENTS.md also exists and CLAUDE.md does not import it: agents that read only AGENTS.md will not see the rules block" if agents else None
        return "CLAUDE.md", note
    if agents:
        return "AGENTS.md", None
    return "AGENTS.md", "tools that read only CLAUDE.md (Claude Code before 2.1.277) need a CLAUDE.md with the line @AGENTS.md"


def same_file(root, a, b):
    """True when two paths relative to the root name one file (a change of case on a file system that ignores it)."""
    try:
        return os.path.samefile(os.path.join(root, a), os.path.join(root, b))
    except OSError:
        return os.path.normpath(a) == os.path.normpath(b)


def first_existing(root, candidates):
    return next((rel for rel in candidates if os.path.isfile(os.path.join(root, rel))), None)


def vision_text(product_doc, folder="docs"):
    """The vision skeleton; with a product document, Mission and Target Users point to it."""
    text = read(os.path.join(TEMPLATES, "vision.md"))
    if not product_doc:
        return text
    link = os.path.relpath(product_doc, folder).replace(os.sep, "/")
    pointer = "Stated in [%s](%s); not restated here. Add a line only for what it does not say." % (product_doc, link)
    text = re.sub(r"(## Mission\n\n).*?(?=\n## )", lambda m: m.group(1) + pointer + "\n", text, flags=re.DOTALL)
    return re.sub(r"(## Target Users\n\n).*?(?=\n## )", lambda m: m.group(1) + pointer + " The actors come from its users.\n", text, flags=re.DOTALL)


def join_agents(text, name_rules):
    """P1: name the rules section in the hot zone's Below: line, add the two keep-in-step rows.

    Returns (the new text, or None when nothing changes; notes for the person)."""
    lines = text.split("\n")
    end = next((i for i, line in enumerate(lines) if line.strip() == MARKER), None)
    if end is None:
        return None, ["AGENTS.md has no hot zone; nothing joined"]
    changed, notes, title = False, [], RULES_HEADING[3:]
    if name_rules:
        below = [i for i in range(end) if lines[i].startswith("Below:")]
        if below and title.lower() not in lines[below[-1]].lower():
            listed = lines[below[-1]][len("Below:"):].strip().rstrip(".")
            lines[below[-1]] = "Below: %s%s." % (listed + ", " if listed else "", title)
            changed = True
        elif not below:
            lines[end:end] = ["Below: %s." % title, ""]
            end += 2
            changed = True
    if "`Specs` line" not in "\n".join(lines[:end]):
        keep = next((i for i in range(end) if lines[i].strip().lower() == "## keep in step"), None)
        starts = []
        if keep is not None:
            j = keep + 1
            while j < end and not lines[j].startswith("## "):
                if lines[j].startswith("- "):
                    starts.append(j)
                elif starts and lines[j].strip() and not lines[j].startswith((" ", "\t")):
                    break          # a paragraph after the list ends it; blank lines between items do not
                j += 1
        if starts:
            lines[starts[-1]:starts[-1]] = list(KEEP_ROWS)
            changed = True
        else:
            notes.append("AGENTS.md has no Keep in step list: add its two rows by hand (references/existing-structure.md)")
    hot = next(i for i, line in enumerate(lines) if line.strip() == MARKER)
    if changed and hot > HOT_CAP:
        return None, ["joining would take the hot zone of AGENTS.md to %d lines (cap %d): shorten it, then run setup again" % (hot, HOT_CAP)]
    return ("\n".join(lines) if changed else None), notes


def join_atlas(text, row):
    """P5: one row for the specifications in the hot zone's map table. Returns (the new text or None, notes)."""
    lines = text.split("\n")
    end = next((i for i, line in enumerate(lines) if line.strip() == MARKER), len(lines))
    if any(line.startswith("| Specifications |") for line in lines[:end]):
        return None, []
    for i in range(end - 1):
        header = [cell.strip() for cell in lines[i].strip().strip("|").split("|")]
        if lines[i].startswith("|") and "Part" in header and "Works through" in header \
                and lines[i + 1].strip().lstrip("|").strip().startswith("-"):
            j = i + 2
            while j < end and lines[j].startswith("|"):
                j += 1
            if end + 1 > HOT_CAP:
                return None, ["a row would take the hot zone of ATLAS.md to %d lines (cap %d): shorten it, then run setup again" % (end + 1, HOT_CAP)]
            lines[j:j] = [row]
            return "\n".join(lines), []
    return None, ["ATLAS.md has no map table in its hot zone: add the specifications row by hand"]


def atlas_row(root, folder, checks_copied):
    """The map row for the specifications; paths in backticks only for what exists once the plan is applied."""
    works = ["`%s/vision.md`" % folder, "`%s/use_cases/`" % folder, "`%s/test_cases/`" % folder]
    for name in ("requirements.md", "entity_model.md", "use_cases.md"):
        if os.path.isfile(os.path.join(root, folder, name)):
            works.append("`%s/%s`" % (folder, name))
    checked = "`tools/specs/`" if checks_copied else "the validator and the lint of the specification skills"
    return "| Specifications | What the system does, written before it is built | %s | — | %s |" % (", ".join(works), checked)


def other_specs(root, folder):
    """Specifications outside the specification folder: [(path, what they look like)]. Nothing is moved.

    A use_cases folder of this method's use cases has its own note; another method's folder that holds it is named
    too when it holds specification documents outside that use_cases folder."""
    ours = []
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        rel = os.path.relpath(base, root).replace(os.sep, "/")
        if os.path.basename(base) == "use_cases" and rel != folder + "/use_cases" \
                and any(re.match(r"UC-\d{3}-.+\.md$", name) for name in files):
            ours.append(rel)
    found = []
    for rel, what in OTHER_SPECS:
        path = os.path.join(root, rel)
        if rel == folder or not os.path.isdir(path):
            continue
        for base, _, files in os.walk(path):
            inner = os.path.relpath(base, root).replace(os.sep, "/")
            if any(inner == other or inner.startswith(other + "/") for other in ours):
                continue
            if any(name.endswith(".md") for name in files):
                found.append((rel, what))
                break
    return found + [(rel, "use cases in this method's format") for rel in ours]


def overview_system(root):
    """Represent the folder name in the model's front-matter subset, losslessly."""
    name = os.path.basename(os.path.abspath(root))
    for candidate in (name, '"' + name + '"', "'" + name + "'"):
        meta, _, problems = spec_model.read_front_matter(('---\nsystem: ' + candidate + '\n---').splitlines())
        if not problems and meta.get('system', (None, 0))[0] == name and name:
            return candidate
    raise ValueError('repository folder name cannot be represented in the front matter subset')


def branch_plan(root, guideline, no_integration_line=False):
    """Return the proposed branch and informational/line steps, without changing rules."""
    target = os.path.join(root, guideline) if guideline else None
    text = read(target) if target and os.path.isfile(target) else ""
    block = text.split(RULES_HEADING, 1)[1] if RULES_HEADING in text else ""
    local_source, local_base = "UP_BASE", os.environ.get("UP_BASE")
    if not local_base:
        local_source = "git config up.base"
        code, configured = spec_model.git(("config", "--get", "up.base"), cwd=root)
        local_base = configured.strip() if code == 0 else None
    if local_base:
        return None, [("info", "", None, "the integration branch is set locally (%s = %s); "
                       "add the rules-block line by hand if the team should share it" % (local_source, local_base))]
    if spec_model.RE_INTEGRATION_BRANCH.search(block):
        return None, []
    if no_integration_line:
        return None, [("info", "", None, "the integration branch line is declined for this run")]
    try:
        base = change_view.detect_base(root)
    except Exception:
        # A setup proposal is optional; a failed detection must not block script updates.
        return None, []
    if base.ref is None:
        return None, []
    branch = base.ref
    if branch.startswith("refs/remotes/"):
        branch = branch[len("refs/remotes/"):].split("/", 1)[1]
    else:
        code, remotes = spec_model.git(("remote",), cwd=root)
        # Refs can survive removal of a remote's configuration; include their remote names too.
        ref_code, refs = spec_model.git(("for-each-ref", "--format=%(refname)", "refs/remotes/"), cwd=root)
        names = set(remotes.splitlines() if code == 0 else ())
        if ref_code == 0:
            names.update(ref[len("refs/remotes/"):].split("/", 1)[0] for ref in refs.splitlines())
        for remote in sorted(names):
            if branch.startswith(remote + "/"):
                branch = branch[len(remote) + 1:]
                break
    note = "integration branch: %s (detected from %s)" % (branch, base.ref)
    steps = []
    if guideline:
        note += "; confirm it with the person"
        steps.append(("line", guideline, branch, "adds the integration branch to the rules block"))
    steps.insert(0, ("info", "", None, note))
    return branch, steps


def update_plan(root: str, replace=(), keep=(), requested=(), no_integration_line=False) -> tuple[list, list[str]]:
    """Classify every known script; return steps and undecided names without writing.

    Requested sets ("hook" or "check") add their missing copies alongside any
    installed sets. Script decisions use bare filenames. Wiring names retain their prefix for
    the wiring planner, which joins this plan in the next setup stage.
    """
    folder = Path(root) / "tools/specs"
    bundle = installed_copies.read_bundle(folder)
    known = json.loads(read(os.path.join(HERE, "known_scripts.json")))["scripts"]
    installed = installed_copies.sets_installed(folder) | set(requested)
    names = sorted(set(installed_copies.HOOK_SET + installed_copies.CHECK_SET))
    states = {name: installed_copies.classify(folder / name, (Path(HERE) / name).read_bytes(), known, bundle)
              for name in names}
    replace, keep = set(replace), set(keep)
    for name in sorted(replace | keep):
        if name.startswith("wiring:"):
            continue
        if name in replace & keep:
            raise ValueError("%s is named in both --replace and --keep" % name)
        if name not in states or not (folder / name).is_file():
            raise ValueError("%s is not a known installed script" % name)
        if states[name] != "changed" and not (states[name] == "kept" and name in replace):
            raise ValueError("%s is not undecided" % name)
    guideline = spec_model.read_rules_block(root)[0]
    _, steps = branch_plan(root, guideline, no_integration_line)
    undecided = []
    entries = bundle.get("scripts", {})
    if not isinstance(entries, dict):
        entries = {}
    for name in names:
        state = states[name]
        rel, source = "tools/specs/" + name, os.path.join(HERE, name)
        if state == "missing":
            needed = ("hook" in installed and name in installed_copies.HOOK_SET or
                      "check" in installed and name in installed_copies.CHECK_SET)
            steps.append(("create" if needed else "skip", rel, (source, None) if needed else None,
                          "missing; added for an installed or requested set" if needed else "missing; set not installed"))
        elif state == "changed":
            before = (folder / name).read_bytes().decode("utf-8", errors="replace")
            after = Path(source).read_bytes().decode("utf-8", errors="replace")
            diff = "".join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                             fromfile=rel, tofile="this release/" + name))
            entry = entries.get(name, {})
            context = ""
            if isinstance(entry, dict) and entry.get("kept") == installed_copies.fingerprint((folder / name).read_bytes()):
                context = "kept on %s; old package baseline %s" % (installed_copies.script_version(folder / name) or "before 1.1.0", entry.get("baseline", "unknown"))
            steps.append(("diff", rel, diff, context))
            action = "replace" if name in replace else "keep" if name in keep else "changed"
            steps.append((action, rel, (source, None), "changed by hand"))
            if action == "changed":
                undecided.append(name)
        elif state == "untouched" or state == "kept" and name in replace:
            steps.append(("replace", rel, (source, None), state))
        else:
            steps.append(("skip", rel, None, state))
    return steps, undecided


def wiring_fingerprint(entry):
    """Hash the command and its generated wrapper in canonical JSON form."""
    return installed_copies.fingerprint(json.dumps(entry, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _inner(entry):
    return {key: value for key, value in entry.items() if key not in ("moment", "event", "matcher")}


def _wiring_by_tool(bundle):
    """Read the bundle's per-tool wiring records."""
    wiring = bundle.get("wiring", {})
    if not isinstance(wiring, dict):
        return {}
    return {tool: record for tool, record in wiring.items()
            if tool in hook_profiles.PROFILES[1:] and isinstance(record, dict)}


def _wrapped_entry(tool, entry):
    """Include every field setup generates that can change a hook's behavior."""
    inner, matcher = _inner(entry), entry["matcher"]
    if tool == "kiro":
        # The stop runs the finish check, so it gets twice the other hooks' minute.
        wrapped = {"name": WIRING_NAMES[entry["moment"]], "trigger": entry["event"], "enabled": True,
                   "timeout": 120 if entry["moment"] == "before-stop" else 60, "action": inner}
    else:
        wrapped = {"hook": inner}
    if matcher is not None:
        wrapped["matcher"] = matcher
    return wrapped


def _old_adapters(root, command):
    """Find repository scripts named by a command that invoke the gate."""
    if root is None:
        return []
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()")
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return []
    found = []
    root = Path(root).resolve()
    for token in tokens:
        path = Path(token)
        if path.is_absolute():
            continue
        path = root / path
        try:
            relative = path.resolve().relative_to(root).as_posix()
            if not path.is_file() or relative == "tools/specs/hook_gate.py":
                continue
            if path.name == "up_hook.py" or WIRING_CALL.search(path.read_text(encoding="utf-8")):
                found.append(relative)
        except (OSError, UnicodeError, ValueError):
            continue
    return sorted(set(found))


def _use_case_dir(root, folder):
    """Use an existing recognized use-case folder, falling back to the canonical name."""
    docs = spec_model.Docs(os.path.join(root, folder))
    path = docs.use_case_dir
    return os.path.relpath(path, root).replace(os.sep, "/") if path else folder + "/use_cases"


def _wiring_nodes(node, tool, moment=None, group=None, wrapper=None, root=None):
    """Find calls with the enclosing matcher or Kiro hook used for fingerprinting."""
    if isinstance(node, dict):
        trigger = node.get("trigger")
        moment = WIRING_MOMENTS.get(trigger, moment) if isinstance(trigger, str) else moment
        if tool == "kiro" and isinstance(trigger, str) and trigger in WIRING_MOMENTS:
            wrapper = node
        if moment and isinstance(node.get("command"), str) and (WIRING_CALL.search(node["command"]) or
                _old_adapters(root, node["command"])):
            wrapped = wrapper if tool == "kiro" and wrapper is not None else dict(group or {}, hook=node)
            yield moment, node, wrapped
        for key, value in node.items():
            matcher = group
            if key == "hooks" and isinstance(value, list):
                matcher = {"matcher": node["matcher"]} if "matcher" in node else {}
            yield from _wiring_nodes(value, tool, WIRING_MOMENTS.get(key, moment), matcher, wrapper, root)
    elif isinstance(node, list):
        for value in node:
            yield from _wiring_nodes(value, tool, moment, group, wrapper, root)


def _remove_wiring(node, removed):
    """Remove selected inner objects; preserve every mixed group's other fields."""
    if isinstance(node, list):
        node[:] = [value for value in node if not isinstance(value, dict) or id(value) not in removed]
        for value in list(node):
            if not isinstance(value, dict):
                continue
            own_action = isinstance(value.get("action"), dict) and id(value["action"]) in removed
            only_ours = (isinstance(value.get("hooks"), list) and bool(value["hooks"]) and
                         all(id(hook) in removed for hook in value["hooks"]))
            if own_action or only_ours:
                node.remove(value)
            else:
                _remove_wiring(value, removed)
    elif isinstance(node, dict):
        for value in node.values():
            _remove_wiring(value, removed)


def _holders(document, ids):
    """The (dict, key, list) event lists that hold a selected node, directly or through its group."""
    found = []

    def holds(value):
        return id(value) in ids or (isinstance(value.get("hooks"), list) and
                                    any(isinstance(hook, dict) and id(hook) in ids for hook in value["hooks"]))

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, list) and any(isinstance(item, dict) and holds(item) for item in value):
                    found.append((node, key, value))
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    walk(document)
    return found


def _prune_emptied(document, tool, holders):
    """Drop only the event lists this run's removal emptied, and an Antigravity group left empty by that."""
    parents = []
    for parent, key, values in holders:
        if values == [] and parent.get(key) is values:
            del parent[key]
            parents.append(parent)
    if tool == "antigravity":
        for name in [name for name, group in document.items() if not group and any(group is p for p in parents)]:
            del document[name]


def _add_wiring(document, tool, entries):
    for entry in entries:
        moment, event, matcher = entry["moment"], entry["event"], entry["matcher"]
        inner = _inner(entry)
        if tool == "kiro":
            document.setdefault("version", "v1")
            document.setdefault("hooks", []).append(_wrapped_entry(tool, entry))
        else:
            hooks = document.setdefault(WIRING_NAMES[moment], {}) if tool == "antigravity" else document.setdefault("hooks", {})
            values = hooks.setdefault(event, [])
            if tool == "antigravity" and matcher is None:
                values.append(inner)
            else:
                group = {"matcher": matcher} if matcher is not None else {}
                group["hooks"] = [inner]
                values.append(group)


def _read_wiring(path, tool):
    """Read plain JSON and remember its indentation and final newline."""
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    document = json.loads(text) if path.exists() else {}
    if not isinstance(document, dict):
        raise ValueError("JSON root must be an object")
    if tool == "kiro":
        if not isinstance(document.get("hooks", []), list):
            raise ValueError("JSON hooks must be an array")
        if "version" in document and document["version"] != "v1":
            raise ValueError("unsupported Kiro JSON version (expected v1)")
    else:
        if tool == "antigravity":
            for name in WIRING_NAMES.values():
                if name in document and not isinstance(document[name], dict):
                    raise ValueError("JSON hook group %s must be an object" % name)
            groups = [value for value in document.values() if isinstance(value, dict)]
        else:
            groups = [document.get("hooks", {})]
        for group in groups:
            if not isinstance(group, dict):
                raise ValueError("JSON hook groups must be objects")
            for event, values in group.items():
                if event in WIRING_MOMENTS and not isinstance(values, list):
                    raise ValueError("JSON event %s must be an array" % event)
    indent = re.search(r"(?m)^([ \t]+)\S", text)
    indent = indent.group(1) if indent else "  "
    return document, indent, not text or text.endswith("\n"), text


def _wiring_diff(before, after, source, target):
    """Keep a unified diff readable when a file's last line has no newline."""
    lines = difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile=source, tofile=target)
    return "".join(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n" for line in lines)


def wiring_plan(root, tool, replace=(), keep=(), reasons=(), use_case_dir=None) -> list:
    """Plan wiring; exact generated sets establish baselines without a rewrite."""
    rel, generated, _ = hook_profiles.wiring(tool, use_case_dir or _use_case_dir(root, spec_model.docs_default(root)))
    choices = {"wiring:" + moment for moment in hook_profiles.MOMENTS}
    replace, keep = set(replace), list(keep)
    wiring_keep = [name for name in keep if name.startswith("wiring:")]
    selected = {name for name in replace | set(keep) if name.startswith("wiring:")}
    if selected - choices or replace & set(keep) & choices:
        raise ValueError("invalid or conflicting wiring decisions: %s" % ", ".join(sorted(selected)))
    if len(reasons) > len(wiring_keep):
        raise ValueError("each --reason needs a --keep wiring:<moment> (in the same order)")
    reason_by_name = dict(zip(wiring_keep, reasons))
    bundle = installed_copies.read_bundle(Path(root) / "tools/specs")
    previous = _wiring_by_tool(bundle).get(tool, {})
    if previous.get("file") != rel:
        previous = {}
    baselines = previous.get("entries", [])
    adapted = previous.get("adapted", [])
    baselines = baselines if isinstance(baselines, list) else []
    adapted = adapted if isinstance(adapted, list) else []
    paths = {rel}
    # Claude loads local settings too; scanning them must never authorize writing them.
    readonly = {".claude/settings.local.json"} if tool == "claude" else set()
    paths.update(name for name in readonly if (Path(root) / name).exists())
    if tool == "kiro":
        paths.update(str(path.relative_to(root)) for path in (Path(root) / ".kiro/hooks").glob("*.json"))
    documents, records, steps = {}, [], []
    for name in sorted(paths):
        try:
            document, indent, newline, text = _read_wiring(Path(root) / name, tool)
        except (OSError, UnicodeError, ValueError) as exc:
            steps.append(("refused", name, None, "cannot read plain JSON: %s" % exc))
            continue
        documents[name] = (document, indent, newline, text)
        records.extend((moment, node, wrapped, name) for moment, node, wrapped in _wiring_nodes(document, tool, root=root))
    if rel not in documents or any(step[0] == "refused" for step in steps):
        return steps
    record = {"tool": tool, "file": rel, "entries": [], "adapted": []}
    removed = set()
    # Entries removed with nothing generated in their place; only containers they leave empty go too.
    emptied = set()
    additions = []
    leftovers = set()
    for moment in hook_profiles.MOMENTS:
        name = "wiring:" + moment
        expected = [entry for entry in generated if entry["moment"] == moment]
        found = [(node, wrapped, path) for found_moment, node, wrapped, path in records if found_moment == moment]
        fingerprints = [wiring_fingerprint(wrapped) for _, wrapped, _ in found]
        wanted = [wiring_fingerprint(_wrapped_entry(tool, entry)) for entry in expected]
        baseline = [entry["fingerprint"] for entry in baselines
                    if isinstance(entry, dict) and entry.get("moment") == moment and isinstance(entry.get("fingerprint"), str)]
        adaptations = [entry for entry in adapted if isinstance(entry, dict) and entry.get("moment") == moment
                       and isinstance(entry.get("fingerprint"), str)]
        if not expected:
            why = "%s: %s is not generated (%s), so the stop carries the specification check" % (
                tool, moment, NOT_GENERATED_WHY.get(tool, "its feedback reaches nobody on this tool"))
            if not found:
                steps.append(("info", rel, None, why))
                if name in selected:
                    raise ValueError("%s has no generated entry" % name)
                continue
            # An entry an earlier release or the person installed stays undecided until it is named.
            targets = sorted({path for node, _, _ in found for path in _old_adapters(root, node["command"])}
                             or {"tools/specs/hook_gate.py"})
            calls = ("an existing entry calls " if len(found) == 1 else "existing entries call ") + ", ".join(targets)
            kept = sorted(fingerprints) == sorted(entry["fingerprint"] for entry in adaptations)
            if name in replace and any(path in readonly for _, _, path in found):
                steps.append(("refused", name, None, ".claude/settings.local.json is read only; remove its hook manually or use --keep " + name))
            elif name in replace:
                for node, _, _ in found:
                    removed.add(id(node))
                    leftovers.update(_old_adapters(root, node["command"]))
                emptied.update(id(node) for node, _, _ in found)
                steps.append(("info", name, None, "%s; %s: removed, nothing generated in its place" % (why, calls)))
            elif name in keep or kept:
                if name in keep:
                    record["adapted"].extend({"moment": moment, "fingerprint": fingerprint,
                                              "reason": reason_by_name.get(name, "kept by the person")}
                                             for fingerprint in fingerprints)
                else:
                    record["adapted"].extend(adaptations)
                steps.append(("keep" if name in keep else "skip", name, None, "%s; %s: kept" % (why, calls)))
            else:
                steps.append(("info", rel, None, "%s; %s: --replace %s removes it, --keep %s keeps it"
                              % (why, calls, name, name)))
                steps.append(("changed", name, None, "moment no longer generated; choose --replace or --keep"))
            continue
        current = bool(found) and sorted(fingerprints) == sorted(wanted)
        kept = not current and bool(found) and sorted(fingerprints) == sorted(entry.get("fingerprint", "") for entry in adaptations)
        untouched = bool(found) and not (Counter(fingerprints) - Counter(baseline))
        local = any(path in readonly for _, _, path in found)
        state = ("current" if current else "kept" if kept else "missing" if not found else
                 "untouched" if untouched and not local else "changed")
        if name in selected and not found:
            raise ValueError("%s is not an installed wiring moment" % name)
        if name in selected and state != "changed" and not (kept and name in replace):
            raise ValueError("%s is not undecided" % name)
        if found and (state == "changed" or name in selected):
            before = json.dumps([wrapped for _, wrapped, _ in found], indent=2, ensure_ascii=False) + "\n"
            after = json.dumps([_wrapped_entry(tool, entry) for entry in expected], indent=2, ensure_ascii=False) + "\n"
            diff = "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                             fromfile="installed/" + name, tofile="generated/" + name))
            steps.append(("diff", name, diff, "in " + ", ".join(sorted({path for _, _, path in found}))))
        if local and name in replace:
            steps.append(("refused", name, None, ".claude/settings.local.json is read only; remove its hook manually or use --keep " + name))
            continue
        if name in keep or kept and name not in replace:
            if name in keep:
                record["adapted"].extend({"moment": moment, "fingerprint": fingerprint,
                                           "reason": reason_by_name.get(name, "kept by the person")}
                                          for fingerprint in fingerprints)
            else:
                record["adapted"].extend(adaptations)
            steps.append(("keep" if name in keep else "skip", name, None, "kept; generated entry omitted"))
        elif state == "changed" and name not in replace:
            steps.append(("changed", name, None, "moment already covered; choose --replace or --keep"))
        elif current and name not in replace:
            # An exact generated set already contains the package's bytes.
            record["entries"].extend({"moment": moment, "fingerprint": fingerprint} for fingerprint in wanted)
            steps.append(("skip", name, None, "current"))
        else:
            retained = Counter()
            for node, wrapped, _ in found:
                fingerprint = wiring_fingerprint(wrapped)
                if name not in replace and fingerprint in wanted:
                    retained[fingerprint] += 1
                    if fingerprint in baseline:
                        record["entries"].append({"moment": moment, "fingerprint": fingerprint})
                else:
                    removed.add(id(node))
                    leftovers.update(_old_adapters(root, node["command"]))
            for entry, fingerprint in zip(expected, wanted):
                if retained[fingerprint]:
                    retained[fingerprint] -= 1
                else:
                    additions.append(entry)
                    record["entries"].append({"moment": moment, "fingerprint": fingerprint})
            steps.append(("info", name, None, "%s: %s; generate in %s" % (name, state, rel)))
    for name, (document, indent, newline, before) in documents.items():
        if name in readonly:
            continue
        holders = _holders(document, emptied)
        _remove_wiring(document, removed)
        _prune_emptied(document, tool, holders)
        if name == rel:
            _add_wiring(document, tool, additions)
        after = json.dumps(document, indent=indent, ensure_ascii=False) + ("\n" if newline else "")
        if document != (json.loads(before) if before else {}):
            diff = _wiring_diff(before, after, name, "generated/" + name)
            steps.append(("diff", name, diff, "planned wiring"))
            steps.append(("wire", name, after, "merge only setup's entries"))
        if (name != rel and not document.get("hooks") and set(document) <= {"version", "hooks"}
                and any(path == name and id(node) in removed for _, node, _, path in records)):
            leftovers.add(name)
    retained_adapters = {path for _, node, _, _ in records if id(node) not in removed
                         for path in _old_adapters(root, node["command"])}
    for name in sorted(leftovers - retained_adapters):
        steps.append(("info", name, None, "left behind: %s; the person may delete it" % name))
    if tool == "kiro":
        # Proven on Kiro CLI 2.33.1 (trial 04): its default engine ignores .kiro/hooks/; setup changes no Kiro setting.
        steps.append(("info", rel, None, "kiro: Kiro CLI runs these hooks only on its V3 engine, so set "
                                         "`kiro-cli settings chat.agentEngine v3`, or start with `kiro-cli chat --v3`"))
    steps.append(("wiring-record", rel, record, "record generated baselines and kept adaptations"))
    return steps


def unrecorded_wiring_notes(root):
    """Point the owner at existing wiring that setup has not recorded yet."""
    for tool in hook_profiles.PROFILES[1:]:
        rel = hook_profiles.wiring(tool, "docs/use_cases")[0]
        paths = {rel}
        if tool == "claude":
            paths.add(".claude/settings.local.json")
        if tool == "kiro":
            paths.update(path.relative_to(root).as_posix() for path in (Path(root) / ".kiro/hooks").glob("*.json"))
        commands = []
        for name in sorted(paths):
            if not (Path(root) / name).is_file():
                continue
            try:
                document, _, _, _ = _read_wiring(Path(root) / name, tool)
            except (OSError, UnicodeError, ValueError):
                continue
            commands.extend(node["command"] for _, node, _ in _wiring_nodes(document, tool, root=root))
        if commands:
            adapters = sorted({path for command in commands for path in _old_adapters(root, command)})
            kind = "old adapter: " + ", ".join(adapters) if adapters else "direct entries"
            yield "wiring for %s found (%s): run --hooks --tool %s to bring it under setup" % (tool, kind, tool)


def ignored_notes(root, folder):
    """Ignored paths are informational; git failures never block setup."""
    for rel, sentence in ((folder, "Ignored specifications are validated at every stop."),
                          (folder + "/change-records", "Ignored change records never open the finish check.")):
        code, _ = spec_model.git(("check-ignore", "-q", "--no-index", "--", rel + "/"), cwd=root)
        if code == 0:
            yield "warning: git ignores %s/. %s" % (rel, sentence)


def plan(root, profile, host, guideline, skipped=(), hooks=False, folder="docs", replace=(), keep=(), no_integration_line=False):
    """Return a list of (action, relative path, source or text, note)."""
    steps = []
    product_doc = first_existing(root, PRODUCT_DOCS)

    def file_step(rel, source=None, text=None):
        if os.path.exists(os.path.join(root, rel)):
            steps.append(("skip", rel, None, "exists, left as it is"))
        else:
            steps.append(("create", rel, (source, text), ""))

    if product_doc and not os.path.exists(os.path.join(root, folder + "/vision.md")):
        steps.append(("create", folder + "/vision.md", (None, vision_text(product_doc, folder)),
                      "skeleton; Mission and Target Users point to %s instead of restating it" % product_doc))
    else:
        file_step(folder + "/vision.md", source=os.path.join(TEMPLATES, "vision.md"))
    if "use case overview" not in skipped:
        file_step(folder + "/use_cases.md", text="---\nsystem: %s\n---\n# Use cases\n\n## Scope\n\n## Delivery order\n\n" % overview_system(root))
    for sub in (_use_case_dir(root, folder), folder + "/test_cases"):
        if os.path.isdir(os.path.join(root, sub)):
            steps.append(("skip", sub + "/", None, "exists"))
        else:
            steps.append(("create", sub + "/.gitkeep", (None, ""), "keeps the empty folder under version control"))

    _, branch_steps = branch_plan(root, guideline, no_integration_line)
    block = rules_block(profile, skipped, folder)
    target = os.path.join(root, guideline)
    if not os.path.exists(target):
        steps.append(("create", guideline, (None, block), "rules block; profile %s" % profile))
    elif RULES_HEADING in read(target):
        steps.append(("skip", guideline, None, "already contains the rules block"))
    else:
        steps.append(("append", guideline, (None, block), "rules block added at the end; existing content untouched"))
    steps.extend(branch_steps)

    copies = list(CHECK_SCRIPTS) if profile == "team" else []
    if hooks:
        copies += [name for name in HOOK_SCRIPTS if name not in copies]
    if os.path.isdir(os.path.join(root, "tools/specs")):
        requested = ({"check"} if profile == "team" else set()) | ({"hook"} if hooks else set())
        updates, _ = update_plan(root, replace, keep, requested=requested, no_integration_line=no_integration_line)
        steps.extend(step for step in updates if step[1].startswith("tools/specs/"))
    else:
        if replace or keep:
            update_plan(root, replace, keep)  # Validate decisions even before any copies exist.
        for name in copies:
            file_step("tools/specs/" + name, source=os.path.join(HERE, name))
    if profile == "team":
        for template, rel in HOST_FILES[host].items():
            file_step(rel, source=os.path.join(TEMPLATES, template))
    if spec_model.a_files_present(root):
        agents = os.path.join(root, "AGENTS.md")
        if os.path.isfile(agents):
            new, notes = join_agents(read(agents), guideline == "AGENTS.md")
            if new is None:
                steps.append(("skip", "AGENTS.md", None, "; ".join(notes) or "already joined to the A-files"))
            else:
                steps.append(("join", "AGENTS.md", guideline == "AGENTS.md",
                              "; ".join(["the rules named in the hot zone, two keep-in-step rows (A-files)"] + notes)))
        atlas = os.path.join(root, "ATLAS.md")
        if os.path.isfile(atlas):
            row = atlas_row(root, folder, bool(copies))
            new, notes = join_atlas(read(atlas), row)
            if new is None and not notes:
                steps.append(("skip", "ATLAS.md", None, "already maps the specifications"))
            elif new is None:
                steps.append(("skip", "ATLAS.md", None, "; ".join(notes)))
            else:
                steps.append(("join", "ATLAS.md", row, "one row for the specifications (A-files)"))
    return steps


def apply(root, steps):
    undecided = [rel for action, rel, _, _ in steps if action in ("changed", "refused")]
    if undecided:
        raise ValueError("undecided installed copies: " + ", ".join(undecided))
    written = set()
    for action, rel, payload, _ in steps:
        if action in ("skip", "info", "diff", "keep", "wiring-record"):
            continue
        target = os.path.join(root, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if action == "wire":
            with open(target, "w", encoding="utf-8") as handle:
                handle.write(payload)
        elif action == "create":
            source, text = payload
            if os.path.exists(target):          # appeared since the plan was made: still never overwrite
                continue
            if source:
                shutil.copyfile(source, target)
                written.add(rel)
            else:
                with open(target, "x", encoding="utf-8") as handle:
                    handle.write(text)
        elif action == "replace":
            shutil.copyfile(payload[0], target)
            written.add(rel)
        elif action == "line":
            current = read(target)
            prefix, block = current.split(RULES_HEADING, 1)
            if not spec_model.RE_INTEGRATION_BRANCH.search(block):
                line = "**Integration branch:** %s" % payload
                match = spec_model.RE_SPECS_FOLDER.search(block)
                if match:
                    pos = block.find("\n", match.start())
                    pos = len(block) if pos == -1 else pos
                else:
                    matches = list(re.finditer(r"(?m)^\*\*(?:Profile|Skipped):\*\*[^\n]*", block))
                    pos = matches[-1].end() if matches else 0
                    line = "**Specs folder:** %s  \n%s" % (spec_model.docs_default(root), line)
                before = block[:pos].rstrip(" \t")
                block = before + ("  \n" if before else "\n\n") + line + block[pos:]
                with open(target, "w", encoding="utf-8") as handle:
                    handle.write(prefix + RULES_HEADING + block)
        elif action == "append":
            source, text = payload
            existing = read(target)
            with open(target, "a", encoding="utf-8") as handle:
                handle.write(("" if existing.endswith("\n") else "\n") + "\n" + text)

        elif action == "join":
            current = read(target)
            new, _ = join_agents(current, payload) if rel == "AGENTS.md" else join_atlas(current, payload)
            if new is not None:
                with open(target, "w", encoding="utf-8") as handle:
                    handle.write(new)

    folder = Path(root) / "tools/specs"
    wiring_records = [payload for action, _, payload, _ in steps if action == "wiring-record"]
    if wiring_records:
        folder.mkdir(parents=True, exist_ok=True)
    if folder.is_dir():
        bundle = installed_copies.read_bundle(folder)
        scripts = bundle.get("scripts", {})
        if not isinstance(scripts, dict):
            scripts = {}
        kept = {rel for action, rel, _, _ in steps if action == "keep"}
        for name in sorted(set(installed_copies.HOOK_SET + installed_copies.CHECK_SET)):
            path = folder / name
            if not path.is_file():
                continue
            current = (Path(HERE) / name).read_bytes()
            installed = path.read_bytes()
            rel = "tools/specs/" + name
            if rel in kept:
                scripts[name] = {"baseline": installed_copies.fingerprint(current),
                                 "kept": installed_copies.fingerprint(installed)}
            elif rel in written or installed == current:
                scripts[name] = {"baseline": installed_copies.fingerprint(current)}
        if wiring_records:
            wiring = _wiring_by_tool(bundle)
            for record in wiring_records:
                wiring[record["tool"]] = record
            bundle["wiring"] = wiring
        if scripts or wiring_records:
            bundle.update(version=installed_copies.UPSPEC_VERSION, scripts=scripts)
            installed_copies.write_bundle(folder, bundle)


def vision_gaps(path):
    """Sections of the vision that are missing, empty or still placeholder text."""
    lines = read(path).split("\n")
    bodies, current = {}, None
    for line in lines:
        heading = re.match(r"^#{2,3}\s+(.*\S)\s*$", line)
        if heading:
            current = heading.group(1).lower()
            bodies[current] = []
        elif current:
            bodies[current].append(line)
    gaps = []
    for section in VISION_SECTIONS:
        if section.lower() not in bodies:
            gaps.append("%s: section missing" % section)
            continue
        text = re.sub(r"<!--.*?-->", "", "\n".join(bodies[section.lower()]), flags=re.DOTALL).strip()
        if not text:
            gaps.append("%s: empty" % section)
        elif PLACEHOLDER.search(text):
            gaps.append("%s: still holds placeholder text" % section)
    return gaps


def main(argv):
    parser = argparse.ArgumentParser(description="Plan or apply the setup for specification-first work.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--profile", choices=("solo", "team"), default="solo")
    parser.add_argument("--host", choices=sorted(HOST_FILES), default="none", help="where pull requests and pipelines live (team profile)")
    parser.add_argument("--specs-folder", help="the specification folder inside the project (default: the recorded one, else docs)")
    parser.add_argument("--guideline", help="guideline file, relative to the root (default: chosen from AGENTS.md and CLAUDE.md)")
    parser.add_argument("--skip", action="append", default=[], choices=sorted(SKIPPABLE),
                        help="solo profile only: an artifact of the chain the owner decided to leave out (repeatable)")
    parser.add_argument("--hooks", action="store_true",
                        help="also copy the gate of the agent hooks and the scripts it calls into tools/specs/")
    parser.add_argument("--tool", choices=hook_profiles.PROFILES[1:], help="generate the chosen tool's project hooks (with --hooks)")
    parser.add_argument("--update", action="store_true", help="plan an update of installed script copies")
    parser.add_argument("--replace", action="append", default=[], metavar="NAME", help="replace a customized copy (repeatable)")
    parser.add_argument("--keep", action="append", default=[], metavar="NAME", help="keep a ported customization (repeatable)")
    parser.add_argument("--reason", action="append", default=[], metavar="TEXT", help="reason for each kept wiring moment, in --keep order (repeatable)")
    parser.add_argument("--no-integration-line", action="store_true", help="decline the integration branch line for this run")
    parser.add_argument("--apply", action="store_true", help="write the files; without it only the plan is printed")
    args = parser.parse_args(argv)
    if args.tool and not args.hooks:
        parser.error("--tool requires --hooks")
    if args.skip and args.profile != "solo":
        print("--skip applies to the solo profile only; a team keeps the full chain", file=sys.stderr)
        return 2
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print("no such folder: %s" % args.root, file=sys.stderr)
        return 2
    tools = [args.tool] if args.tool else []
    if args.update and not args.hooks and not tools:
        tools = list(_wiring_by_tool(installed_copies.read_bundle(Path(root) / "tools/specs")))
    wiring_decisions = args.reason or any(name.startswith("wiring:") for name in args.replace + args.keep)
    if wiring_decisions and not tools:
        parser.error("wiring decisions and --reason require --hooks --tool, or --update with a recorded tool")
    if wiring_decisions and len(tools) > 1:
        parser.error("wiring decisions for several recorded tools need --hooks --tool to select one")
    folder = (args.specs_folder or spec_model.docs_default(root)).rstrip("/")
    real = os.path.realpath(os.path.join(root, folder))
    if folder.startswith("/") or not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", folder) \
            or any(part in (".", "..") for part in folder.split("/")) or not real.startswith(os.path.realpath(root) + os.sep):
        print("--specs-folder must be a folder inside the project, such as docs, specs or documentation/specs", file=sys.stderr)
        return 2
    stop = spec_model.stop_if_old(spec_model.Docs(real))
    if stop:
        return stop
    if "diagram" in args.skip:
        print("note: --skip diagram is an alias for --skip overview")
    try:
        guideline, guideline_note = pick_guideline(root, args.guideline)
    except (OSError, UnicodeDecodeError) as exc:
        print("cannot read the guideline file: %s" % exc, file=sys.stderr)
        return 2
    if os.path.isabs(guideline) or ".." in guideline.replace("\\", "/").split("/"):
        print("--guideline must be a path inside the root", file=sys.stderr)
        return 2
    try:
        # The rules block the scripts read is in AGENTS.md or CLAUDE.md; a project keeps one.
        names = ["AGENTS.md", "CLAUDE.md"]
        if not any(same_file(root, guideline, name) for name in names):
            names.append(guideline)
        holders = [name for name in names
                   if os.path.isfile(os.path.join(root, name)) and RULES_HEADING in read(os.path.join(root, name))]
        if args.specs_folder is not None and holders:
            recorded = (spec_model.recorded_docs(root) or "docs").rstrip("/")
            if folder != recorded:
                print("--specs-folder requested %s, but the rules block in %s records %s; add or edit **Specs folder:** %s in "
                      "the rules block before setup" % (folder, holders[0], recorded, folder), file=sys.stderr)
                return 2
        if holders and not any(same_file(root, guideline, name) for name in holders):
            print("the rules block is already in %s: a project keeps one; run setup with --guideline %s, or move the "
                  "block into %s first" % (holders[0], holders[0], guideline), file=sys.stderr)
            return 2
        if args.update:
            steps, undecided = update_plan(root, args.replace, args.keep,
                                            requested=("hook",) if args.hooks else (),
                                            no_integration_line=args.no_integration_line)
        else:
            steps = plan(root, args.profile, args.host, guideline, [SKIPPABLE[name] for name in sorted(set(args.skip))],
                         args.hooks, folder=folder, replace=args.replace, keep=args.keep,
                         no_integration_line=args.no_integration_line)
            undecided = [rel.rsplit("/", 1)[-1] for action, rel, _, _ in steps if action == "changed"]
        branch_info = any(step[0] == "info" for step in steps)
        if tools:
            for tool in tools:
                steps.extend(wiring_plan(root, tool, args.replace, args.keep, args.reason, _use_case_dir(root, folder)))
        elif args.update and not args.hooks:
            steps.extend(("info", "", None, note) for note in unrecorded_wiring_notes(root))
        elif args.hooks:
            steps.append(("info", "", None, "Scripts only; add --tool claude|codex|antigravity|kiro to plan wiring."))
        undecided = [rel if rel.startswith("wiring:") or action == "refused" else rel.rsplit("/", 1)[-1]
                     for action, rel, _, _ in steps if action in ("changed", "refused")]
        existing_rules = read(os.path.join(root, guideline)) if os.path.isfile(os.path.join(root, guideline)) else ""
        branch_unknown = not branch_info and not spec_model.RE_INTEGRATION_BRANCH.search(
            existing_rules.split(RULES_HEADING, 1)[1] if RULES_HEADING in existing_rules else "")
        refused = args.apply and bool(undecided)
        if args.apply and not refused:
            apply(root, steps)
    except (OSError, UnicodeDecodeError, ValueError, change_view.BaseError) as exc:
        print("cannot complete the setup: %s" % exc, file=sys.stderr)
        return 2

    header = "Applied" if args.apply and not refused else "Plan: nothing written; add --apply to write"
    if args.update:
        _, profile, _ = spec_model.read_rules_block(root)
        _, block = spec_model._rules_block_text(root)
        host = re.search(r"(?mi)^\*\*Host:\*\*\s*(github|gitlab|none)\b", block or "")
        details = (["profile " + profile] if profile else []) + (["host " + host.group(1).lower()] if host else [])
    else:
        details = ["profile " + args.profile, "host " + args.host]
    print(header + (" (" + ", ".join(details) + ")" if details else ""))
    for action, rel, payload, note in steps:
        if action == "info":
            print(note)
        elif action == "diff":
            if note:
                print("  %s: %s" % (rel, note))
            print(payload, end="" if payload.endswith("\n") else "\n")
        else:
            print("  %-6s %s%s" % (action, rel, "  (%s)" % note if note else ""))
    pending = sum(1 for step in steps if step[0] in ("create", "replace", "append", "join", "line", "keep", "wire"))
    print("%d to write, %d left as they are" % (pending, sum(step[0] == "skip" for step in steps)))
    if refused:
        for name in undecided:
            if any(action == "refused" and rel == name for action, rel, _, _ in steps):
                remedy = "resolve the read-only hook" if name.startswith("wiring:") else "fix the JSON file"
                print("refused: %s; %s before applying; nothing written" % (name, remedy), file=sys.stderr)
            else:
                print("undecided: %s; use --replace %s or --keep %s; nothing written" % (name, name, name), file=sys.stderr)
    if branch_unknown:
        print("integration branch could not be detected; add **Integration branch:** by hand")
    for note in ignored_notes(root, folder):
        print(note)
    if not args.update and args.profile == "team" and args.host != "github":
        print("note: no pipeline job was planned for host '%s'; run the two commands from the team instruments reference in its pipeline" % args.host)
    if args.hooks:
        print("note: let the person turn the hooks on in the tool, prove each moment, and commit the wiring on its own"
              if args.tool else "note: wire the hooks into the agent's tool as references/agent-hooks.md says, let the person turn them on, "
              "prove each one, and commit them on their own")
    for path, what in other_specs(root, folder):
        print("note: specifications found in %s (%s): ask whether to align them fully (into %s/) or keep them; "
              "see references/existing-structure.md" % (path, what, folder))
    if spec_model.a_files_present(root):
        print("note: this project tracks its work in the A-files: after --apply, run python3 tools/check_tracking.py; "
              "it must print nothing")
    if guideline_note:
        print("note: %s" % guideline_note)
    glossary = first_existing(root, GLOSSARIES)
    if glossary:
        print("note: %s holds the project's vocabulary; the entity model and the specifications take its terms" % glossary)

    vision = os.path.join(root, folder, "vision.md")
    if os.path.isfile(vision):
        gaps = vision_gaps(vision)
        print("vision: %s" % ("every section is written" if not gaps else "%d section(s) still to write" % len(gaps)))
        for gap in gaps:
            print("  %s" % gap)
    print("Next: commit tools/specs/ and the wiring on their own (setup step 6).")
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
