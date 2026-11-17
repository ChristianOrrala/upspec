#!/usr/bin/env python3
"""Set a repository up for specification-first work: plan first, apply on request, decide customized copies.

Both profiles:
  docs/vision.md                       skeleton for a person to fill in
  docs/use_cases/, docs/test_cases/    empty folders, kept with a .gitkeep
  the guideline file                   gets the rules block appended once (created if absent)

Team profile, in addition:
  tools/specs/                         copies of the check scripts, so the pipeline needs nothing installed
  the pull request template and the pipeline job of the chosen host

Setup writes no agent hooks: the plugins carry them. --update retires what an earlier
release installed for them: its entries in the tool's hook files, its hook-only copies in tools/specs/ and the
**Hooks:** line of the rules block.

When the project tracks its work in the A-files (ACTIVE.md with a hot zone), the
plan also joins them: the rules section is named in the hot zone of AGENTS.md,
the keep-in-step list gains two rows when the project keeps ABILITIES.md (the
file exists or the index of AGENTS.md lists it), and ATLAS.md, when it exists,
gains a row for the specifications. Specifications found outside the specification folder (this
method's use cases elsewhere, Spec Kit's specs/, Kiro's .kiro/specs/,
OpenSpec's openspec/) are named in a note; nothing is moved.

Without --apply nothing is written: the plan is printed. Setup keeps existing
documents and appends the rules block once. It proposes a missing integration
branch line and joins the A-files once. --update refreshes installed scripts, the recorded CI workflow and the package pre-push hook, and retires the
agent wiring of an earlier release in the same all-or-nothing plan.
Untouched copies are replaced. Customized copies show a diff and need an
explicit --replace NAME or --keep NAME decision before any file is written.
The bundle records package baselines and fingerprints of kept customizations.
--update treats the rules block of the guideline file the same way, under the
name guideline:rules-block. A block exactly as a release wrote it (its field
lines and specification folder aside) is replaced whole by the current
template and keeps its own field lines; a block the owner edited shows its
diff and needs --replace guideline:rules-block or --keep guideline:rules-block;
a keep is recorded in the bundle and offered again only when the block or the
template changes. The rest of the guideline file is never touched, and a
project without a rules block gets none from --update.
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
                     [--guideline FILE] [--specs-folder DIR] [--skip requirements|overview|entity-model ...] [--pre-push]
                     [--update] [--replace NAME ...] [--keep NAME ...] [--no-integration-line] [--apply]

--update --replace guideline:rules-block replaces an edited rules block with the current
template and its own field lines; --keep guideline:rules-block records that it stays as edited.

--update retires an earlier release's hook wiring: it removes only the entries that run
tools/specs/hook_gate.py from .claude/settings.json, .codex/hooks.json, .agents/hooks.json and
.kiro/hooks/upspec.json (a file that held nothing else goes too), keeping every other entry and byte.
An entry changed by hand needs --replace wiring:<moment> or --keep wiring:<moment>. After the update
tools/specs/ holds the check scripts when the project uses them (team profile, the recorded pipeline job or
pre-push hook) and otherwise only spec_data.py. Unreadable JSON or an undecided entry prevents every write.
--hooks, --tool and --reason no longer exist (exit 2).

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
import difflib
import json
import os
import re
import shutil
from pathlib import Path
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model  # noqa: E402  (local module, same folder)
import change_view  # noqa: E402
import installed_copies  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(os.path.dirname(HERE), "templates")
RULES_HEADING = "## Working from specifications"
# The name under which --update offers the rules block of the guideline file for --replace and --keep.
RULES_NAME = "guideline:rules-block"
# The line of the template that setup fills with the profile and the other field lines.
PROFILE_LINE = "**Profile:** [solo | team]"
# The lines of the rules block that belong to the project, not to the template.
RE_FIELD = re.compile(r"^\*\*(Profile|Hooks|Skipped|Specs folder|Integration branch|Host):\*\*[ \t]*(.*?)[ \t]*$", re.MULTILINE | re.IGNORECASE)
# The paths a recorded specification folder replaces in the template, as `docs/` plus these.
BLOCK_PATHS = ("", "use_cases/", "requirements.md", "entity_model.md")
# CI claims need the finish check and its dependencies, without agent wiring.
CHECK_SCRIPTS = ("spec_model.py", "validate_use_case.py", "spec_lint.py", "use_case_map.py", "spec_first_guard.py",
                 "status_claims.py", "finish_change.py", "scope_audit.py", "uc_change_list.py",
                 "unrecorded_changes.py", "change_view.py", "spec_data.py")
# The check set ends with the model command (spec_data.py), which no check runs: it is there so that a program can
# read the project's model through the project's own copy, whichever profile is installed. A project without the
# check set keeps only that one copy of the scripts.
PLUGIN_HOOKS_NOTE = ("The plugin now carries the agent hooks: Claude Code turns them on with the plugin, Codex asks you to "
                     "approve them in /hooks, and Kiro and OpenCode take the files the manual names.")
MODEL_SCRIPTS = ("spec_model.py", "spec_data.py")      # spec_data.py imports spec_model.py from its own folder
# What an earlier release also copied for the agent hooks (installed_copies.HOOK_SET); --update retires it.
RE_HOOKS_LINE = re.compile(r"^\*\*Hooks:\*\*.*(?:\r?\n|$)", re.MULTILINE | re.IGNORECASE)
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
# Event names an earlier release's wiring used, per research 12 (Kiro's file variant included).
WIRING_MOMENTS = {"SessionStart": "session-start", "PostToolUse": "after-edit",
                  "PostFileSave": "after-edit", "PostFileCreate": "after-edit", "Stop": "before-stop", "UserPromptSubmit": "turn-start"}
# An entry whose command runs the gate an earlier release copied into the project.
WIRING_CALL = re.compile(r"(?:^|[\s\"'/])tools/specs/hook_gate\.py(?=$|[\s\"';])")


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _template_text(folder="docs"):
    """The template with the specification folder in its paths and the profile line still to fill."""
    text = read(os.path.join(TEMPLATES, "guideline-rules.md"))
    if folder != "docs":
        for name in BLOCK_PATHS:
            text = text.replace("`docs/%s`" % name, "`%s/%s`" % (folder, name))
    return text


def rules_block(profile, skipped=(), folder="docs", branch=None):
    """The rules block with the profile filled in, and the artifacts a solo project decided to leave out."""
    line = "**Profile:** %s" % profile
    if skipped:
        line += "  \n**Skipped:** %s" % ", ".join(skipped)
    if folder != "docs" or branch:
        line += "  \n**Specs folder:** %s" % folder
    if branch:
        line += "  \n**Integration branch:** %s" % branch
    return _template_text(folder).replace(PROFILE_LINE, line).rstrip("\n") + "\n"


def block_span(text):
    """(start, end) of the rules block in a guideline file's text: from the heading at the start of a line to the
    next line that starts with '## ', or the end of the file. None when the file has no such heading."""
    heading = re.search(r"^" + re.escape(RULES_HEADING), text, re.MULTILINE)
    if not heading:
        return None
    following = re.compile(r"^## ", re.MULTILINE).search(text, heading.end())
    return heading.start(), following.start() if following else len(text)


def _block_folder(block):
    match = spec_model.RE_SPECS_FOLDER.search(block)
    return match.group(1).replace("\\", "/").rstrip("/") or "docs" if match else "docs"


def normalized_block(block):
    """The block as the template wrote it: its field lines put back to the template's profile line, and the
    specification folder in its paths put back to docs/. Trailing whitespace and the line-ending style do not count."""
    text = block.replace("\r\n", "\n")
    folder = _block_folder(text)
    if folder != "docs":
        for name in BLOCK_PATHS:
            text = text.replace("`%s/%s`" % (folder, name), "`docs/%s`" % name)
    lines = []
    for line in text.split("\n"):
        field = RE_FIELD.match(line)
        if field and field.group(1).lower() == "profile":
            lines.append(PROFILE_LINE)
        elif not field:
            lines.append(line)
    return "\n".join(lines).rstrip()


def block_fingerprint(block):
    """The fingerprint known_scripts.json keeps for a released template: that of the normalized block."""
    return installed_copies.fingerprint(normalized_block(block).encode("utf-8"))


def renewed_block(block):
    """The current template with the block's own field lines, in their order, and its specification folder."""
    text = block.replace("\r\n", "\n")
    labels = {"profile": "Profile", "skipped": "Skipped", "specs folder": "Specs folder",
              "integration branch": "Integration branch", "host": "Host"}
    # The Hooks line of an earlier release is not carried over: the plugins carry the hooks now.
    found = [match for match in RE_FIELD.finditer(text) if match.group(1).lower() != "hooks"]
    fields = "  \n".join("**%s:** %s" % (labels[match.group(1).lower()], match.group(2)) for match in found)
    return _template_text(_block_folder(text)).replace(PROFILE_LINE, fields).rstrip("\n") + "\n"


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


def keeps_abilities(root, agents_text):
    """Whether the project keeps ABILITIES.md: the file exists, or the index of AGENTS.md lists it, read as the
    A-files' check reads it (spec_model.a_files_listed). A small A-files setup keeps no abilities, so nothing is
    said about them."""
    return (os.path.isfile(os.path.join(root, "ABILITIES.md"))
            or "ABILITIES.md" in spec_model.a_files_listed(agents_text.split("\n")))


def join_agents(text, name_rules, abilities):
    """P1: name the rules section in the hot zone's Below: line; add the two keep-in-step rows when the project
    keeps ABILITIES.md (abilities).

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
    if abilities and "`Specs` line" not in "\n".join(lines[:end]):
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


def workflow_text(root, proposed_branch=None):
    """Render the shared integration branch as a quoted YAML value, never shell code."""
    _, block = spec_model._rules_block_text(root)
    match = spec_model.RE_INTEGRATION_BRANCH.search(block or "")
    branch = match.group(1) if match else proposed_branch or ""
    return read(os.path.join(TEMPLATES, "ci-github.yml")).replace(
        "__UP_INTEGRATION_BRANCH__", json.dumps(branch))


def workflow_plan(root, bundle, replace=(), keep=(), proposed_branch=None):
    """Treat a recorded workflow like a script; unrecorded files need a decision."""
    name, rel = "ci:specifications", HOST_FILES["github"]["ci-github.yml"]
    path = Path(root) / rel
    if not path.is_file():
        if name in replace or name in keep:
            raise ValueError("%s is not an installed workflow" % name)
        return []
    text = workflow_text(root, proposed_branch)
    state = installed_copies.classify(path, text.encode("utf-8"), {}, bundle,
                                      name=name, section="files", require_record=True)
    if name in replace and name in keep:
        raise ValueError("%s is named in both --replace and --keep" % name)
    if name in set(replace) | set(keep) and not (state == "changed" or state == "kept" and name in replace):
        raise ValueError("%s is not undecided" % name)
    steps = []
    if state in ("untouched", "changed") or state == "kept" and name in replace:
        diff = "".join(difflib.unified_diff(read(path).splitlines(keepends=True), text.splitlines(keepends=True),
                                         fromfile=rel, tofile="this release/" + rel))
        steps.append(("diff", rel, diff, state))
        action = ("replace" if state == "untouched" or name in replace else
                  "keep" if name in keep else "changed")
        steps.append((action, rel, (None, text), state))
    else:
        steps.append(("skip", rel, None, state))
    steps.append(("file-record", rel, (name, text), "package baseline"))
    return steps


def pre_push_plan(root, bundle, requested=False):
    """Install only in repository-owned hooks; refresh only a recorded pristine copy."""
    # The line reports and lets the push go ahead; a strict push gate adds --strict and drops "|| true".
    command = 'python3 tools/specs/status_claims.py --pre-push "$@" || true'
    offer = ("info", "", None, "Optional local push report: add --pre-push --apply; it never stops a push unless --strict is added.")
    records = bundle.get("files", {})
    entry = records.get("pre-push", {}) if isinstance(records, dict) else {}
    if not isinstance(entry, dict):
        entry = {}
    if not requested and not entry:
        return [offer]
    code, hooks = spec_model.git(("rev-parse", "--git-path", "hooks"), cwd=root)
    git_code, git_dir = spec_model.git(("rev-parse", "--absolute-git-dir"), cwd=root)
    common_code, common_dir = spec_model.git(("rev-parse", "--git-common-dir"), cwd=root)
    if code or git_code or common_code:
        return [("info", "", None, "No repository hooks folder; add this line to your pre-push hook: " + command)]
    root_path = Path(root).resolve()
    folder = (root_path / hooks.strip()).resolve()
    git_path = (root_path / git_dir.strip()).resolve()
    # Linked worktrees share the repository's own hooks in the common Git folder.
    common_path = (root_path / common_dir.strip()).resolve()
    path = folder / "pre-push"
    resolved = path.resolve()
    inside = any(resolved == base or base in resolved.parents for base in (root_path, git_path, common_path))
    if not inside:
        return [("info", "", None, "Hooks folder is outside the repository; add this line there: " + command)]
    rel = os.path.relpath(path, root_path).replace(os.sep, "/")
    text = read(os.path.join(TEMPLATES, "pre-push.sh"))
    steps = []
    if root_path in folder.parents or folder == root_path:
        tracked_code, tracked = spec_model.git(("ls-files", "--", os.path.relpath(folder, root_path)), cwd=root)
        if tracked_code == 0 and tracked.strip():
            steps.append(("info", rel, None, "Tracked hooks folder %s: this hook will be committed for every clone." % hooks.strip()))
    if path.exists() or path.is_symlink():
        # Existing hooks belong to their owner; only our exact recorded package baseline may refresh.
        managed = isinstance(entry, dict) and entry.get("path") == rel and not path.is_symlink()
        state = (installed_copies.classify(path, text.encode("utf-8"), {}, bundle,
                                          name="pre-push", section="files", require_record=True)
                 if managed and path.is_file() else "changed")
        if state not in ("current", "untouched"):
            return steps + [("info", rel, None, "Existing pre-push (changed by hand or unrecorded), never edited; add: " + command)]
        steps.append(("replace" if state == "untouched" else "skip", rel, (None, text), state))
    else:
        steps.append(("create", rel, (None, text), "optional local check; CI stays authoritative"))
    steps.append(("file-record", rel, ("pre-push", text), "executable package hook"))
    return steps


def read_guideline(root, guideline):
    """The guideline file's text with its line endings as they are, and the span of its rules block (or None)."""
    with open(os.path.join(root, guideline), encoding="utf-8", newline="") as handle:
        text = handle.read()
    return text, block_span(text)


def rules_block_plan(root, guideline, bundle, known, replace=(), keep=()):
    """Treat the rules block of the guideline file like an installed script; return the steps, without writing.

    The block is current (the current template), kept (an edit recorded as kept against this template),
    untouched (exactly a released template, field lines and specification folder aside) or changed by hand.
    A guideline file without the block gets no step: --update never adds one."""
    named = RULES_NAME in set(replace) | set(keep)
    if RULES_NAME in set(replace) & set(keep):
        raise ValueError("%s is named in both --replace and --keep" % RULES_NAME)
    block = None
    if guideline and os.path.isfile(os.path.join(root, guideline)):
        text, span = read_guideline(root, guideline)
        block = text[span[0]:span[1]] if span else None
    if block is None:
        if named:
            raise ValueError("%s is not an installed rules block" % RULES_NAME)
        return []
    current = block_fingerprint(_template_text())
    installed = block_fingerprint(block)
    raw = installed_copies.fingerprint(block.replace("\r\n", "\n").rstrip().encode("utf-8"))
    entry = bundle.get("files", {}).get(RULES_NAME, {}) if isinstance(bundle.get("files", {}), dict) else {}
    if not isinstance(entry, dict):
        entry = {}
    if installed == current:
        state = "current"
    elif entry.get("kept") == raw:
        state = "kept" if entry.get("baseline") == current else "changed"
    elif installed in known.get("guideline-rules.md", ()):
        state = "untouched"
    else:
        state = "changed"
    if named and not (state == "changed" or state == "kept" and RULES_NAME in replace):
        raise ValueError("%s is not undecided" % RULES_NAME)
    if state in ("current", "kept") and RULES_NAME not in replace:
        return [("skip", RULES_NAME, None, "%s: %s" % (guideline, "kept as edited" if state == "kept" else "current"))]
    before = block.replace("\r\n", "\n").rstrip("\n") + "\n"
    diff = "".join(difflib.unified_diff(before.splitlines(keepends=True), renewed_block(block).splitlines(keepends=True),
                                     fromfile=guideline, tofile="this release/" + guideline))
    note = ("%s: " % guideline) + {"untouched": "as a release wrote it", "kept": "kept as edited",
                                  "changed": "changed by hand"}[state]
    steps = [("diff", guideline, diff, "rules block " + state)]
    if state == "untouched" or RULES_NAME in replace:
        steps.append(("replace", RULES_NAME, (guideline, installed), note))
    elif RULES_NAME in keep:
        steps.append(("keep", RULES_NAME, (guideline, current), note))
    else:
        steps.append(("changed", RULES_NAME, (guideline, installed), note))
    return steps


def check_set_in_use(root, folder, bundle, requested=(), pre_push=False):
    """Whether the project runs the check scripts from tools/specs/: the team profile (its copy of spec_first_guard.py or spec_lint.py, the two scripts only the check set has),
    the recorded or present pipeline job, or the recorded pre-push hook."""
    files = bundle.get("files", {})
    return (bool({"check"} & (installed_copies.sets_installed(folder) | set(requested))) or pre_push
            or any((folder / name).is_file() for name in ("spec_lint.py", "spec_first_guard.py"))
            or (Path(root) / HOST_FILES["github"]["ci-github.yml"]).is_file()
            or isinstance(files, dict) and "pre-push" in files)


def hooks_line_step(root, guideline):
    """The step that removes the **Hooks:** line an earlier release's rules block recorded, or None."""
    if not guideline or not os.path.isfile(os.path.join(root, guideline)):
        return None
    text, span = read_guideline(root, guideline)
    if span is None or not RE_HOOKS_LINE.search(text[span[0]:span[1]]):
        return None
    return ("unline", guideline, None, "removes the **Hooks:** line; the plugins carry the hooks now")


def remove_hooks_line(root, guideline):
    """Remove the **Hooks:** line from the rules block, byte for byte otherwise. The line before it loses its
    two-space line break when no other field line follows."""
    path = os.path.join(root, guideline)
    text, span = read_guideline(root, guideline)
    if span is None:
        return
    block = text[span[0]:span[1]]
    match = RE_HOOKS_LINE.search(block)
    if not match:
        return
    before, after = block[:match.start()], block[match.end():]
    if not RE_FIELD.match(after) and re.search(r"(?<=\S)  \r?\n$", before):
        before = re.sub(r"  (\r?\n)$", r"\1", before)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text[:span[0]] + before + after + text[span[1]:])


def update_plan(root: str, replace=(), keep=(), requested=(), no_integration_line=False, pre_push=False,
                retire=True) -> tuple[list, list[str]]:
    """Classify every known script; return steps and undecided names without writing.

    The check set (CHECK_SCRIPTS) is in use for the team profile, the recorded pipeline job or pre-push hook, or
    when requested; otherwise only the model command and its reader stay. With retire, the rest of what an earlier
    release installed (the hook-only copies, the agent wiring, the Hooks line) is removed in the same plan;
    without it (a setup run) those are left as they are. Script decisions use bare filenames; wiring decisions are
    named wiring:<moment>.
    """
    folder = Path(root) / "tools/specs"
    bundle = installed_copies.read_bundle(folder)
    released = json.loads(read(os.path.join(HERE, "known_scripts.json")))
    known, templates = released["scripts"], released.get("templates", {})
    if not isinstance(templates, dict) or any(
            not isinstance(hashes, list) or not all(isinstance(item, str) for item in hashes)
            for hashes in templates.values()):
        raise ValueError("known_scripts.json: \"templates\" must map each template name to a list of hashes; "
                         "the file is damaged, reinstall the plugin")
    checks = check_set_in_use(root, folder, bundle, requested, pre_push)
    wanted = set(CHECK_SCRIPTS if checks else MODEL_SCRIPTS)
    # An installation exists when the folder holds any copy or record; a solo project gets nothing new from setup.
    held = folder.is_dir() and (bool(bundle) or any((folder / name).is_file() for name in installed_copies.HOOK_SET + installed_copies.CHECK_SET))
    names = sorted(set(installed_copies.HOOK_SET + installed_copies.CHECK_SET))
    states = {name: installed_copies.classify(folder / name, (Path(HERE) / name).read_bytes(), known, bundle)
              for name in names}
    replace, keep = set(replace), set(keep)
    for name in sorted(replace | keep):
        if name.startswith("wiring:") or name in ("ci:specifications", RULES_NAME):
            continue
        if name in replace & keep:
            raise ValueError("%s is named in both --replace and --keep" % name)
        if name not in states or not (folder / name).is_file():
            raise ValueError("%s is not a known installed script" % name)
        if states[name] != "changed" and not (states[name] == "kept" and name in replace):
            raise ValueError("%s is not undecided" % name)
    guideline = spec_model.read_rules_block(root)[0]
    branch, steps = branch_plan(root, guideline, no_integration_line)
    steps.extend(rules_block_plan(root, guideline, bundle, templates, replace, keep))
    undecided = []
    entries = bundle.get("scripts", {})
    if not isinstance(entries, dict):
        entries = {}
    for name in names:
        state = states[name]
        rel, source = "tools/specs/" + name, os.path.join(HERE, name)
        if name not in wanted:
            if not retire:
                steps.append(("skip", rel, None, state if state == "missing" else "not part of the installed set; --update retires it"))
            elif state == "missing":
                steps.append(("skip", rel, None, "missing; set not installed"))
            elif state == "kept" and name not in replace:
                steps.append(("skip", rel, None, "kept as you changed it"))
            elif name in replace:
                steps.append(("remove", rel, None, "changed by hand; removed by decision, outside the installed set"))
            elif state in ("current", "untouched"):
                steps.append(("remove", rel, None, "an earlier release's copy; the plugins carry the agent hooks now"))
            elif name in keep:
                steps.append(("keep", rel, (source, None), "changed by hand; kept by decision, outside the installed set"))
            else:
                steps.append(("changed", rel, (source, None), "changed by hand and no longer in the installed set; "
                              "--replace %s removes it, --keep %s keeps it" % (name, name)))
                undecided.append(name)
            continue
        if state == "missing":
            needed = checks or held
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
    steps.extend(workflow_plan(root, bundle, replace, keep, branch))
    steps.extend(pre_push_plan(root, bundle, pre_push))
    if any(action == "changed" and rel == HOST_FILES["github"]["ci-github.yml"]
           for action, rel, _, _ in steps):
        undecided.append("ci:specifications")
    if any(action == "changed" and rel == RULES_NAME for action, rel, _, _ in steps):
        undecided.append(RULES_NAME)
    if retire:
        line = hooks_line_step(root, guideline)
        if line:
            steps.append(line)
        steps.extend(wiring_retirement_plan(root, bundle, replace, keep))
        if any(action in ("remove", "wire", "unline") for action, _, _, _ in steps):
            steps.append(("closing", "", None, PLUGIN_HOOKS_NOTE))
    elif replace & {name for name in replace if name.startswith("wiring:")} or keep & {name for name in keep if name.startswith("wiring:")}:
        raise ValueError("wiring decisions belong to --update")
    return steps, undecided


# The project files an earlier release wired the agent hooks into, with the tool each one served; --update retires them.
WIRING_FILES = {".claude/settings.json": "claude", ".codex/hooks.json": "codex",
                ".agents/hooks.json": "antigravity", ".kiro/hooks/upspec.json": "kiro"}
# Claude Code's personal settings were scanned, never written; they still are not.
LOCAL_SETTINGS = ".claude/settings.local.json"
MOMENTS = ("session-start", "after-edit", "before-stop", "turn-start")


def wiring_fingerprint(entry):
    """Hash the command and its wrapper in canonical JSON form, as earlier releases recorded it."""
    return installed_copies.fingerprint(json.dumps(entry, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _old_commands(tool):
    """The command lines earlier releases generated for a tool: with no record in the bundle, only these count as untouched."""
    found = set()
    for moment in MOMENTS:
        invocation = "python3 tools/specs/hook_gate.py %s --emit %s" % (moment, tool)
        if moment == "turn-start":
            found.add('{ root="$(git rev-parse --show-toplevel 2>/dev/null)" && cd "$root" && [ -f tools/specs/hook_gate.py ] && '
                      + invocation + '; } 2>/dev/null || exit 0')
        elif tool == "kiro":
            found.add('{ root="$(git rev-parse --show-toplevel)" && cd "$root" && [ -f tools/specs/hook_gate.py ] && '
                      + invocation + '; } || exit 3')
        else:
            found.add('cd "$(git rev-parse --show-toplevel)" && if [ -f tools/specs/hook_gate.py ]; then ' + invocation + '; fi')
    return found


def _wiring_records(bundle):
    """The bundle's per-tool wiring records of earlier releases."""
    wiring = bundle.get("wiring", {})
    if not isinstance(wiring, dict):
        return {}
    return {tool: record for tool, record in wiring.items() if tool in WIRING_FILES.values() and isinstance(record, dict)}


def _wiring_nodes(node, tool, moment=None, group=None, wrapper=None):
    """Find the entries that run the gate, with the enclosing matcher or Kiro hook used for fingerprinting."""
    if isinstance(node, dict):
        trigger = node.get("trigger")
        moment = WIRING_MOMENTS.get(trigger, moment) if isinstance(trigger, str) else moment
        if tool == "kiro" and isinstance(trigger, str) and trigger in WIRING_MOMENTS:
            wrapper = node
        if moment and isinstance(node.get("command"), str) and WIRING_CALL.search(node["command"]):
            wrapped = wrapper if tool == "kiro" and wrapper is not None else dict(group or {}, hook=node)
            yield moment, node, wrapped
        for key, value in node.items():
            matcher = group
            if key == "hooks" and isinstance(value, list):
                matcher = {"matcher": node["matcher"]} if "matcher" in node else {}
            yield from _wiring_nodes(value, tool, WIRING_MOMENTS.get(key, moment), matcher, wrapper)
    elif isinstance(node, list):
        for value in node:
            yield from _wiring_nodes(value, tool, moment, group, wrapper)


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
    """The (dict, key, list) event lists that hold a selected node, directly or through its group or Kiro hook."""
    found = []

    def holds(value):
        return (id(value) in ids or isinstance(value.get("action"), dict) and id(value["action"]) in ids or
                isinstance(value.get("hooks"), list) and any(isinstance(hook, dict) and id(hook) in ids for hook in value["hooks"]))

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


def _prune_emptied(document, holders):
    """Drop only the event lists this run's removal emptied, and the top-level group they leave empty."""
    parents = []
    for parent, key, values in holders:
        if values == [] and parent.get(key) is values:
            del parent[key]
            parents.append(parent)
    for name in [name for name, group in document.items() if group == {} and any(group is p for p in parents)]:
        del document[name]


def _read_wiring(path):
    """Read plain JSON and remember its indentation and final newline."""
    text = path.read_text(encoding="utf-8")
    document = json.loads(text)
    if not isinstance(document, dict):
        raise ValueError("JSON root must be an object")
    indent = re.search(r"(?m)^([ \t]+)\S", text)
    return document, indent.group(1) if indent else "  ", not text or text.endswith("\n"), text


def _wiring_diff(before, after, source, target):
    """Keep a unified diff readable when a file's last line has no newline."""
    lines = difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile=source, tofile=target)
    return "".join(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n" for line in lines)


def wiring_retirement_plan(root, bundle, replace=(), keep=()) -> list:
    """Plan the removal of the agent wiring an earlier release installed, without writing.

    Only entries whose command runs tools/specs/hook_gate.py go; every other entry, key, order, indentation and
    character stays. An entry as a release wrote it (recorded in the bundle, or exactly a generated command line) is
    untouched and goes; one changed by hand waits for --replace wiring:<moment> or --keep wiring:<moment>."""
    replace, keep = set(replace), set(keep)
    choices = {"wiring:" + moment for moment in MOMENTS}
    selected = {name for name in replace | keep if name.startswith("wiring:")}
    if selected - choices or replace & keep & choices:
        raise ValueError("invalid or conflicting wiring decisions: %s" % ", ".join(sorted(selected)))
    records, steps, eligible = {}, [], set()
    listed = set()
    previous = _wiring_records(bundle)
    for rel, tool in WIRING_FILES.items():
        path = Path(root) / rel
        if not path.is_file():
            continue
        try:
            document, indent, newline, text = _read_wiring(path)
        except (OSError, UnicodeError, ValueError) as exc:
            steps.append(("refused", rel, None, "cannot read plain JSON: %s" % exc))
            continue
        found = list(_wiring_nodes(document, tool))
        if not found:
            continue
        record = previous.get(tool, {})
        if record.get("file") != rel:
            record = {}
        baseline = {item.get("fingerprint") for item in record.get("entries", []) if isinstance(item, dict)}
        adapted = {item.get("fingerprint"): item for item in record.get("adapted", []) if isinstance(item, dict)}
        generated = _old_commands(tool)
        removed, kept = set(), []
        for moment, node, wrapped in found:
            name, fingerprint = "wiring:" + moment, wiring_fingerprint(wrapped)
            held = adapted.get(fingerprint)
            # An entry an earlier release recorded as adapted is still upspec's: it calls the gate this update removes.
            # Only one kept by a decision of this release (marked "decision") stays kept.
            state = ("untouched" if fingerprint in baseline else
                     "kept" if held and held.get("decision") == "keep" else
                     "adapted" if held else
                     "untouched" if node["command"] in generated else "changed")
            if state in ("changed", "adapted") or state == "kept" and name in replace:
                eligible.add(name)
            if state == "adapted" and name not in keep:
                removed.add(id(node))
                steps.append(("info", rel, None, "adapted entry for %s (%s): removed; the plugin's hooks replace it"
                              % (moment, held.get("reason", "no reason recorded"))))
            elif state == "untouched" or name in replace:
                removed.add(id(node))
            elif state == "kept" or name in keep:
                kept.append({"moment": moment, "fingerprint": fingerprint, "decision": "keep",
                             "reason": adapted.get(fingerprint, {}).get("reason", "kept by the person")})
            elif name not in listed:
                listed.add(name)
                before = json.dumps(wrapped, indent=2, ensure_ascii=False) + "\n"
                steps.append(("diff", name, _wiring_diff(before, "", "installed/" + name, "this release/" + name), "in " + rel))
                steps.append(("changed", name, None, "changed by hand; --replace %s removes it, --keep %s keeps it" % (name, name)))
        if kept:
            records[tool] = {"tool": tool, "file": rel, "entries": [], "adapted": kept}
        if not removed:
            continue
        holders = _holders(document, removed)
        _remove_wiring(document, removed)
        _prune_emptied(document, holders)
        if document.get("hooks") in ({}, []):
            del document["hooks"]       # the container this removal emptied; the file stays unless nothing else was in it
        after = json.dumps(document, indent=indent, ensure_ascii=False) + ("\n" if newline else "")
        empty = tool != "claude" and set(document) <= {"version"}
        steps.append(("diff", rel, _wiring_diff(text, "" if empty else after, rel, "/dev/null" if empty else "this release/" + rel), "retired wiring"))
        if empty:
            steps.append(("remove", rel, None, "only upspec's hook entries were in it"))
        else:
            steps.append(("wire", rel, after, "removes only upspec's hook entries"))
    for name in sorted(selected - eligible):
        raise ValueError("%s is not an undecided wiring entry" % name)
    local = Path(root) / LOCAL_SETTINGS
    if local.is_file():
        try:
            if list(_wiring_nodes(_read_wiring(local)[0], "claude")):
                steps.append(("info", LOCAL_SETTINGS, None, "%s runs the gate of an earlier release; it is a personal file and is "
                                                              "never edited: remove its upspec hook entries by hand" % LOCAL_SETTINGS))
        except (OSError, UnicodeError, ValueError):
            pass
    if "wiring" in bundle or records:
        steps.append(("wiring-record", "tools/specs", records, "wiring is no longer recorded, except entries kept by decision"))
    return steps


def _use_case_dir(root, folder):
    """Use an existing recognized use-case folder, falling back to the canonical name."""
    docs = spec_model.Docs(os.path.join(root, folder))
    path = docs.use_case_dir
    return os.path.relpath(path, root).replace(os.sep, "/") if path else folder + "/use_cases"


def ignored_notes(root, folder):
    """Ignored paths are informational; git failures never block setup."""
    for rel, sentence in ((folder, "Ignored specifications are checked locally; CI cannot read ignored files."),
                          (folder + "/change-records", "Ignored change records never open the finish check.")):
        code, _ = spec_model.git(("check-ignore", "-q", "--no-index", "--", rel + "/"), cwd=root)
        if code == 0:
            yield "warning: git ignores %s/. %s" % (rel, sentence)


def plan(root, profile, host, guideline, skipped=(), folder="docs", replace=(), keep=(), no_integration_line=False, pre_push=False):
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

    branch, branch_steps = branch_plan(root, guideline, no_integration_line)
    block = rules_block(profile, skipped, folder)
    target = os.path.join(root, guideline)
    if not os.path.exists(target):
        steps.append(("create", guideline, (None, block), "rules block; profile %s" % profile))
    elif RULES_HEADING in read(target):
        steps.append(("skip", guideline, None, "already contains the rules block"))
    else:
        steps.append(("append", guideline, (None, block), "rules block added at the end; existing content untouched"))
    steps.extend(branch_steps)

    copies = list(CHECK_SCRIPTS) if profile == "team" or pre_push else []
    if os.path.isdir(os.path.join(root, "tools/specs")):
        requested = {"check"} if profile == "team" or pre_push else set()
        updates, _ = update_plan(root, replace, keep, requested=requested, no_integration_line=no_integration_line,
                                 retire=False)
        steps.extend(step for step in updates if step[1].startswith("tools/specs/"))
    else:
        if replace or keep:
            update_plan(root, replace, keep, retire=False)  # Validate decisions even before any copies exist.
        for name in copies:
            file_step("tools/specs/" + name, source=os.path.join(HERE, name))
    if profile == "team":
        for template, rel in HOST_FILES[host].items():
            if template == "ci-github.yml":
                file_step(rel, text=workflow_text(root, branch))
                if not os.path.exists(os.path.join(root, rel)):
                    steps.append(("file-record", rel, ("ci:specifications", workflow_text(root, branch)), "rendered baseline"))
            else:
                file_step(rel, source=os.path.join(TEMPLATES, template))
    if spec_model.a_files_present(root):
        agents = os.path.join(root, "AGENTS.md")
        if os.path.isfile(agents):
            text = read(agents)
            abilities = keeps_abilities(root, text)
            new, notes = join_agents(text, guideline == "AGENTS.md", abilities)
            if new is None:
                steps.append(("skip", "AGENTS.md", None, "; ".join(notes) or "already joined to the A-files"))
            else:
                done = "the rules named in the hot zone, two keep-in-step rows" if abilities else "the rules named in the hot zone"
                steps.append(("join", "AGENTS.md", (guideline == "AGENTS.md", abilities),
                              "; ".join([done + " (A-files)"] + notes)))
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
    steps.extend(pre_push_plan(root, installed_copies.read_bundle(Path(root) / "tools/specs"), pre_push))
    return steps


def add_branch_line(root, block, branch):
    """The rules block (the text after the heading, line endings as they are) with the integration branch line added,
    and the lines that were added: the branch line, and a specs folder line when the block had none. The new line
    takes the line ending of the line it sits beside; every other byte stays."""
    line = "**Integration branch:** %s" % branch
    match = spec_model.RE_SPECS_FOLDER.search(block)
    if match:
        pos = block.find("\n", match.start())
        pos = len(block) if pos == -1 else pos
        added = [line]
    else:
        matches = list(re.finditer(r"(?m)^\*\*(?:Profile|Skipped):\*\*[^\r\n]*", block))
        pos = matches[-1].end() if matches else 0
        added = ["**Specs folder:** %s" % spec_model.docs_default(root), line]
    if match and pos > 0 and block[pos - 1:pos] == "\r":
        pos -= 1
    eol = "\r\n" if block[pos:pos + 2] == "\r\n" else "\n" if block[pos:pos + 1] == "\n" else \
        "\r\n" if "\r\n" in block else "\n"
    before = block[:pos].rstrip(" \t")
    return before + ((" " * 2 + eol) if before else eol + eol) + (" " * 2 + eol).join(added) + block[pos:], added


def rewrite_block(root, guideline, planned):
    """Replace the rules block with the current template and the block's own field lines.

    The block is read again, because an earlier step of the plan may have added a field line to it; it must still be
    the block the plan was made for (the same fingerprint, field lines aside). Everything outside the block, its
    line endings and the whitespace after it are written back as they were."""
    path = os.path.join(root, guideline)
    text, span = read_guideline(root, guideline)
    if span is None or block_fingerprint(text[span[0]:span[1]]) != planned:
        raise ValueError("the rules block in %s changed since the plan; run --update again" % guideline)
    block = text[span[0]:span[1]]
    body = block.rstrip()
    new = renewed_block(body).rstrip("\n")
    if "\r\n" in block:
        new = new.replace("\n", "\r\n")
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text[:span[0]] + new + block[len(body):] + text[span[1]:])


def apply(root, steps):
    undecided = [rel for action, rel, _, _ in steps if action in ("changed", "refused")]
    if undecided:
        raise ValueError("undecided installed copies: " + ", ".join(undecided))
    written = set()
    for action, rel, payload, _ in steps:
        if action in ("skip", "info", "diff", "keep", "wiring-record", "file-record", "closing"):
            continue
        if action == "unline":
            remove_hooks_line(root, rel)
            continue
        if rel == RULES_NAME:
            rewrite_block(root, *payload)
            continue
        target = os.path.join(root, rel)
        if action != "remove":
            os.makedirs(os.path.dirname(target), exist_ok=True)
        if action == "remove":
            if os.path.isfile(target) or os.path.islink(target):
                os.unlink(target)
        elif action == "wire":
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
                written.add(rel)
        elif action == "replace":
            source, text = payload
            if source:
                shutil.copyfile(source, target)
            else:
                with open(target, "w", encoding="utf-8") as handle:
                    handle.write(text)
            written.add(rel)
        elif action == "line":
            # The file's own line endings stay: it is read and written untranslated.
            with open(target, encoding="utf-8", newline="") as handle:
                current = handle.read()
            prefix, block = current.split(RULES_HEADING, 1)
            if not spec_model.RE_INTEGRATION_BRANCH.search(block):
                block, _ = add_branch_line(root, block, payload)
                with open(target, "w", encoding="utf-8", newline="") as handle:
                    handle.write(prefix + RULES_HEADING + block)
        elif action == "append":
            source, text = payload
            existing = read(target)
            with open(target, "a", encoding="utf-8") as handle:
                handle.write(("" if existing.endswith("\n") else "\n") + "\n" + text)

        elif action == "join":
            current = read(target)
            new, _ = join_agents(current, *payload) if rel == "AGENTS.md" else join_atlas(current, payload)
            if new is not None:
                with open(target, "w", encoding="utf-8") as handle:
                    handle.write(new)

    folder = Path(root) / "tools/specs"
    wiring_records = [payload for action, _, payload, _ in steps if action == "wiring-record"]
    file_records = [(rel, payload) for action, rel, payload, _ in steps if action == "file-record"]
    block_keeps = [payload for action, rel, payload, _ in steps if action == "keep" and rel == RULES_NAME]
    block_replaced = any(action == "replace" and rel == RULES_NAME for action, rel, _, _ in steps)
    if wiring_records or file_records or block_keeps:
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
                scripts.pop(name, None)         # removed (or never there): no baseline left to keep
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
            # Wiring is retired: only an entry kept by decision is remembered, so that it is not asked again.
            bundle.pop("wiring", None)
            kept_wiring = {tool: record for records in wiring_records for tool, record in records.items()}
            if kept_wiring:
                bundle["wiring"] = kept_wiring
        files = bundle.get("files", {})
        if not isinstance(files, dict):
            files = {}
        for rel, (name, text) in file_records:
            path = Path(root) / rel
            if not path.is_file():
                continue
            baseline = installed_copies.fingerprint(text.encode("utf-8"))
            installed = installed_copies.fingerprint(path.read_bytes())
            if rel in written or installed == baseline or rel in kept:
                files[name] = {"path": rel, "baseline": baseline}
                if rel in kept:
                    files[name]["kept"] = installed
                if name == "pre-push" and rel in written:
                    # Git ignores non-executable hooks; preserve permissions and add executable bits.
                    path.chmod(path.stat().st_mode | 0o111)
        for guideline, baseline in block_keeps:
            # Recorded after every write of the plan, so that the fingerprint is of the block as it now stands.
            text, span = read_guideline(root, guideline)
            files[RULES_NAME] = {"path": guideline, "baseline": baseline, "kept": installed_copies.fingerprint(
                text[span[0]:span[1]].replace("\r\n", "\n").rstrip().encode("utf-8"))}
        # A replaced block is current again: an older keep of it no longer says anything.
        dropped = block_replaced and files.pop(RULES_NAME, None) is not None
        if files:
            bundle["files"] = files
        elif dropped:
            bundle.pop("files", None)
        if scripts or wiring_records or files or dropped:
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
    parser.add_argument("--pre-push", action="store_true", help="offer a local claims check in the repository hooks folder")
    parser.add_argument("--update", action="store_true", help="plan an update of installed script copies, the recorded CI workflow and the rules block of the guideline file, and retire the agent wiring of an earlier release")
    parser.add_argument("--replace", action="append", default=[], metavar="NAME", help="replace a customized copy, or with --update an edited rules block (guideline:rules-block) (repeatable)")
    parser.add_argument("--keep", action="append", default=[], metavar="NAME", help="keep a ported customization, or with --update an edited rules block (guideline:rules-block) (repeatable)")
    parser.add_argument("--no-integration-line", action="store_true", help="decline the integration branch line for this run")
    parser.add_argument("--apply", action="store_true", help="write the files; without it only the plan is printed")
    for flag in ("--hooks", "--tool", "--reason"):
        if any(word == flag or word.startswith(flag + "=") for word in argv):
            parser.error("%s no longer exists: the upspec plugin carries the agent hooks (hooks/ in the plugin), and setup "
                         "writes none; scaffold_docs.py --update retires the wiring an earlier release installed" % flag)
    args = parser.parse_args(argv)
    if not args.update and RULES_NAME in args.replace + args.keep:
        parser.error("%s is decided with --update (--update --replace %s or --update --keep %s)" % (RULES_NAME, RULES_NAME, RULES_NAME))
    if args.skip and args.profile != "solo":
        print("--skip applies to the solo profile only; a team keeps the full chain", file=sys.stderr)
        return 2
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print("no such folder: %s" % args.root, file=sys.stderr)
        return 2
    folder = (args.specs_folder or spec_model.docs_default(root)).rstrip("/")
    inside = "--specs-folder must be a folder inside the project, such as docs, specs or documentation/specs"
    if folder.startswith("/") or not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", folder) \
            or any(part in (".", "..") for part in folder.split("/")):
        print(inside, file=sys.stderr)
        return 2
    # A link that cannot be resolved on the way to the specification folder is named first, as UNREADABLE (exit 1):
    # resolved, its path would name a folder that is not there, and setup would write beside the link or call it outside.
    parts = folder.split("/")
    for depth in range(1, len(parts) + 1):
        here = os.path.join(root, *parts[:depth])
        if spec_model.unresolved_link(here):
            return spec_model.stop_if_old(spec_model.Docs(here), strict=True)
    real = os.path.realpath(os.path.join(root, folder))
    if not real.startswith(os.path.realpath(root) + os.sep):
        print(inside, file=sys.stderr)
        return 2
    # Setup cannot do its work without the file: an unreadable one stops it with 1.
    stop = spec_model.stop_if_old(spec_model.Docs(real), strict=True)
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
                                            no_integration_line=args.no_integration_line, pre_push=args.pre_push)
        else:
            steps = plan(root, args.profile, args.host, guideline, [SKIPPABLE[name] for name in sorted(set(args.skip))],
                         folder=folder, replace=args.replace, keep=args.keep,
                         no_integration_line=args.no_integration_line, pre_push=args.pre_push)
            undecided = [rel.rsplit("/", 1)[-1] for action, rel, _, _ in steps if action == "changed"]
        # Optional hook offers are informational too; only a branch note resolves this question.
        branch_info = any(action == "info" and "integration branch" in note
                          for action, _, _, note in steps)
        undecided = [rel if rel.startswith("wiring:") or action == "refused" else
                     "ci:specifications" if rel == HOST_FILES["github"]["ci-github.yml"] else rel.rsplit("/", 1)[-1]
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
        elif action == "closing":
            continue
        elif action == "file-record":
            continue
        elif action == "diff":
            if note:
                print("  %s: %s" % (rel, note))
            print(payload, end="" if payload.endswith("\n") else "\n")
        else:
            print("  %-6s %s%s" % (action, rel, "  (%s)" % note if note else ""))
            if action == "line" and args.update and not (args.apply and not refused):
                # Show what the line step adds, next to the rules-block diff.
                path = os.path.join(root, rel)
                text = read(path).replace("\r\n", "\n") if os.path.isfile(path) else ""
                if RULES_HEADING in text:
                    for added in add_branch_line(root, text.split(RULES_HEADING, 1)[1], payload)[1]:
                        print("    + %s" % added)
    pending = sum(1 for step in steps if step[0] in ("create", "replace", "append", "join", "line", "keep", "wire", "remove", "unline"))
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
    print("Next: commit what setup wrote, tools/specs/ included, on its own (setup step 6).")
    for action, _, _, note in steps:
        if action == "closing":
            print(note)
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
