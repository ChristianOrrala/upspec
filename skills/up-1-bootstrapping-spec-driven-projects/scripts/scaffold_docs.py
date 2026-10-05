#!/usr/bin/env python3
"""Set a repository up for specification-first work: plan first, apply on request, never overwrite.

Both profiles:
  docs/vision.md                       skeleton for a person to fill in
  docs/use_cases/, docs/test_cases/    empty folders, kept with a .gitkeep
  the guideline file                   gets the rules block appended once (created if absent)

Team profile, in addition:
  tools/specs/                         copies of the check scripts, so the pipeline needs nothing installed
  the pull request template and the pipeline job of the chosen host

With --hooks, either profile:
  tools/specs/                         the gate of the agent hooks (hook_gate.py) and the scripts it
                                       calls; wiring them into the agent's tool follows references/agent-hooks.md

When the project tracks its work in the A-files (ACTIVE.md with a hot zone), the
plan also joins them: the rules section is named in the hot zone of AGENTS.md,
the keep-in-step list gains two rows, and ATLAS.md gains a row for the
specifications. Specifications found outside the specification folder (this
method's use cases elsewhere, Spec Kit's specs/, Kiro's .kiro/specs/,
OpenSpec's openspec/) are named in a note; nothing is moved.

Without --apply nothing is written: the plan is printed. An existing file is
never replaced. The only changes to existing files are the rules block appended
to the guideline file, once, and the joining edits of the A-files, once.

When docs/vision.md exists, the sections that are missing or still hold
placeholder text are listed.

When the project already has a product document (PRODUCT.md, VISION.md, a PRD,
docs/product.md ...), the new vision does not restate it: its Mission and Target
Users sections point to that document. A project glossary found on the way is
named in the plan, so that the entity model takes its terms.

Exit code 0, 2 on usage errors.

Usage:
    scaffold_docs.py [--root DIR] [--profile solo|team] [--host github|gitlab|none]
                     [--guideline FILE] [--specs-folder DIR] [--skip requirements|diagram|entity-model ...] [--hooks] [--apply]

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
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model  # noqa: E402  (local module, same folder)

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(os.path.dirname(HERE), "templates")
RULES_HEADING = "## Working from specifications"
CHECK_SCRIPTS = ("spec_model.py", "validate_use_case.py", "spec_lint.py", "spec_first_guard.py")
# The gate of the agent hooks and every script it calls; copied together so that the gate runs from the project.
HOOK_SCRIPTS = ("hook_gate.py", "workflow_state.py", "validate_use_case.py", "finish_change.py", "scope_audit.py",
                "uc_change_list.py", "unrecorded_changes.py", "spec_model.py")
VISION_SECTIONS = ("Mission", "Target Users", "Goals", "Core Terms", "In Scope", "Out of Scope", "Neighboring Systems",
                   "Constraints", "Success Measures")
# What a solo project may leave out, and the words recorded for it in the rules block.
SKIPPABLE = {"requirements": "requirements catalog", "diagram": "use case diagram", "entity-model": "entity model"}
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


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def rules_block(profile, skipped=(), folder="docs"):
    """The rules block with the profile filled in, and the artifacts a solo project decided to leave out."""
    text = read(os.path.join(TEMPLATES, "guideline-rules.md"))
    line = "**Profile:** %s" % profile
    if skipped:
        line += "  \n**Skipped:** %s" % ", ".join(skipped)
    if folder != "docs":
        line += "  \n**Specs folder:** %s" % folder
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
    for name in ("requirements.md", "entity_model.md", "use_cases.puml"):
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


def plan(root, profile, host, guideline, skipped=(), hooks=False, folder="docs"):
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
    for sub in (folder + "/use_cases", folder + "/test_cases"):
        if os.path.isdir(os.path.join(root, sub)):
            steps.append(("skip", sub + "/", None, "exists"))
        else:
            steps.append(("create", sub + "/.gitkeep", (None, ""), "keeps the empty folder under version control"))

    block = rules_block(profile, skipped, folder)
    target = os.path.join(root, guideline)
    if not os.path.exists(target):
        steps.append(("create", guideline, (None, block), "rules block; profile %s" % profile))
    elif RULES_HEADING in read(target):
        steps.append(("skip", guideline, None, "already contains the rules block"))
    else:
        steps.append(("append", guideline, (None, block), "rules block added at the end; existing content untouched"))

    copies = list(CHECK_SCRIPTS) if profile == "team" else []
    if hooks:
        copies += [name for name in HOOK_SCRIPTS if name not in copies]
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
    for action, rel, payload, _ in steps:
        if action == "skip":
            continue
        target = os.path.join(root, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if action == "create":
            source, text = payload
            if os.path.exists(target):          # appeared since the plan was made: still never overwrite
                continue
            if source:
                shutil.copyfile(source, target)
            else:
                with open(target, "x", encoding="utf-8") as handle:
                    handle.write(text)
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
    parser.add_argument("--apply", action="store_true", help="write the files; without it only the plan is printed")
    args = parser.parse_args(argv)
    if args.skip and args.profile != "solo":
        print("--skip applies to the solo profile only; a team keeps the full chain", file=sys.stderr)
        return 2
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print("no such folder: %s" % args.root, file=sys.stderr)
        return 2
    folder = (args.specs_folder or spec_model.docs_default(root)).rstrip("/")
    real = os.path.realpath(os.path.join(root, folder))
    if folder.startswith("/") or not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", folder) \
            or any(part in (".", "..") for part in folder.split("/")) or not real.startswith(os.path.realpath(root) + os.sep):
        print("--specs-folder must be a folder inside the project, such as docs, specs or documentation/specs", file=sys.stderr)
        return 2
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
        steps = plan(root, args.profile, args.host, guideline, [SKIPPABLE[name] for name in sorted(set(args.skip))], args.hooks, folder=folder)
        if args.apply:
            apply(root, steps)
    except (OSError, UnicodeDecodeError) as exc:
        print("cannot complete the setup: %s" % exc, file=sys.stderr)
        return 2

    print("%s (profile %s, host %s)" % ("Applied" if args.apply else "Plan: nothing written; add --apply to write", args.profile, args.host))
    for action, rel, _, note in steps:
        print("  %-6s %s%s" % (action, rel, "  (%s)" % note if note else ""))
    pending = sum(1 for step in steps if step[0] != "skip")
    print("%d to write, %d left as they are" % (pending, len(steps) - pending))
    if args.profile == "team" and args.host != "github":
        print("note: no pipeline job was planned for host '%s'; run the two commands from the team instruments reference in its pipeline" % args.host)
    if args.hooks:
        print("note: wire the hooks into the agent's tool as references/agent-hooks.md says, let the person turn them on, "
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
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
