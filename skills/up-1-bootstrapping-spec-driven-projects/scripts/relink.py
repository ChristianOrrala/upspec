#!/usr/bin/env python3
"""Move files and keep every reference to them working: plan, apply, verify.

Used when a project adopts a method's layout (the root and docs/) and when
converted files are archived or removed. A move is OLD NEW (a file or a folder,
relative to the root); NEW given as - means the file is removed.
Repeat --keep FILE for records of the moves that must remain as written; when
an interrupted apply moved a record, name it where it was or where it is.

What it recognizes, in the project's text files:
  Markdown  links and images, also in angle brackets ([x](<a b.md>));
            reference-style definitions ([x]: path); @file imports; paths
            written out in prose, tables or backticks, relative to the root,
            with an optional :line or :first-last suffix. Links inside code
            (fenced blocks, inline code) are left alone.
  Others    settings, CI, hook files and scripts: paths relative to the root,
            and paths starting with ./ or ../ relative to the file's own folder
            (recomputed when that file moves).
REWRITE  an exact reference to an old path; apply rewrites it.
KEPT     a mention in a --keep FILE record, left as written and not a problem.
DECIDE   a bare file name in prose or alone in backticks (it may be relative
         to its file's folder), a folder name alone in a setting, a
         reference to a removed file, a #section link into a file that another
         one was merged into; a person decides.
Symbolic links are never followed: a symbolic link is neither read nor
written, and a move whose source or target folder resolves outside the root,
or whose path goes through a symbolic link, is refused.

  plan    lists every REWRITE, DECIDE and KEPT, and the links already broken.
          Moves that interact (a new path inside another move's old path, two
          moves to one place or one inside the other) are refused, also when
          only case tells the paths apart on a file system that ignores it; so
          is a folder's change of case whose free name (OLD.relink-case) is taken
          or is another move's destination.
  apply   checks every move first (no moves that interact, nothing through a
          symbolic link), computes every rewritten file and keeps it in a
          journal (relink-journal.json in the git folder, or .relink-journal.json
          at the root without git) with a fingerprint of each file's text before
          the change and of what each move carries, then moves (git mv in a git
          work tree; a folder into an existing folder file by file; a change of
          case only is a rename, a folder's through a free name), then writes
          each file whole (a temporary file renamed over it), then removes the
          journal and verifies. An interrupted apply is finished by running
          apply again with the same moves. It first checks every recorded move:
          a new path that holds anything but what this apply moved there, a file
          to remove that changed, and a removal or a move through a symbolic
          link are named and nothing moves; a finished change of case is checked
          against its fingerprint like any other move, and a file edited in
          between is never overwritten. The journal stays until they are
          settled. It refuses a move whose new path is another existing file:
          merge the content first and remove the old file.
  verify  every relative Markdown link, image, definition and @file import
          resolves, and its #section exists when it points into another
          Markdown file; a root-absolute link (/guide) that matches no file is
          a WARN (it may be a site route); no exact reference to an old path
          remains (STALE). A bare name still in prose, and a ./ or ../ path in a
          setting that points at nothing, are WARN.

What it cannot see: references from outside the repository, paths built at
run time, and reference forms other than these.

Exit code 0 clean, 1 problems or a refused move, 2 usage.

Usage:
    relink.py plan   --move OLD NEW [--move OLD NEW ...] [--keep FILE ...] [--root DIR] [--format text|json]
    relink.py apply  --move OLD NEW [--move OLD NEW ...] [--keep FILE ...] [--root DIR]
    relink.py verify [--move OLD NEW ...] [--keep FILE ...] [--root DIR]

Requires Python 3.9+, standard library only; git for the moves and the list of
files (without git every file under the root is read, except dependency and
build folders).
"""
import argparse
import errno
import hashlib
import json
import os
import posixpath
import re
import shutil
import stat
import subprocess
import sys
import tempfile

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "target", "__pycache__", ".tox", ".mypy_cache"}
# A larger file is data, not a document an agent keeps in step; reading it would only slow the check.
TEXT_LIMIT = 2000000
MARKDOWN = (".md", ".markdown", ".mdx")
INSTRUCTION_FILES = {"AGENTS.md", "CLAUDE.md", "GEMINI.md", "CONVENTIONS.md", ".cursorrules", ".windsurfrules",
                     ".clinerules", ".github/copilot-instructions.md"}
INSTRUCTION_FOLDERS = (".cursor/rules/", ".github/instructions/", ".kiro/steering/", ".windsurf/rules/",
                       ".clinerules/", ".agents/rules/")
LINK = re.compile(r"(!?\[[^\]\n]*\]\()(<[^>\n]+>|[^)\s]+)((?:\s+\"[^\"]*\")?\))")
DEFINITION = re.compile(r"^(\s{0,3}\[[^\]\n]+\]:\s*)(<[^>\n]+>|\S+)")
IMPORT = re.compile(r"(?<![\w@`/])@([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)")
CODE_SPAN = re.compile(r"(`+)(.+?)\1")
# A path written out: several segments, or one file name with an extension; an optional :line or :first-last.
PATH_TOKEN = re.compile(r"(?<![\w./@:<=?#&-])((?:\.{1,2}/)*[\w.-]+(?:/[\w.-]+)+/?|[\w-][\w.-]*\.[A-Za-z0-9]{1,5})(:\d+(?:-\d+)?)?(?![\w/-])")
FENCE = re.compile(r"^\s*(`{3}|~{3})")
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
EXPLICIT_ID = re.compile(r"""\{#([\w-]+)\}|<a\s+(?:name|id)=["']([^"']+)["']""")
JOURNAL = "relink-journal.json"

# A moved file is hashed in blocks of 1 MiB: it may be large (an image, a data file), and a block bounds the memory used.
BLOCK = 1 << 20
# git cannot rename a folder by case alone on a file system that ignores case ("Invalid argument"): the folder passes
# through this free name next to it, in two git mv steps.
CASE_STEP = ".relink-case"


class UsageError(Exception):
    pass


class Moves:
    """The moves, as (old, new or None) pairs of normalized root-relative paths."""

    def __init__(self, pairs):
        self.pairs = pairs

    def lookup(self, path):
        """('same' | 'moved' | 'removed', path after the moves)."""
        for old, new in self.pairs:
            if path == old or path.startswith(old + "/"):
                if new is None:
                    return "removed", None
                return "moved", new + path[len(old):]
        return "same", path


def norm(path):
    """A posix path without '.' parts, with '..' resolved as far as it goes; '' is the root."""
    parts = []
    for part in path.replace("\\", "/").split("/"):
        if part in ("", "."):
            continue
        if part == ".." and parts and parts[-1] != "..":
            parts.pop()
        else:
            parts.append(part)
    return "/".join(parts)


def parse_moves(raw):
    pairs, seen = [], set()
    for old, new in raw or []:
        for value in (old, new):
            if value != "-" and (os.path.isabs(value) or norm(value).split("/")[0] in ("..", "")):
                raise UsageError("a move must stay inside the root: %s" % value)
        old_n = norm(old)
        if old_n in seen:
            raise UsageError("%s is moved twice" % old)
        for previous in seen:
            if old_n.startswith(previous + "/") or previous.startswith(old_n + "/"):
                raise UsageError("move sources overlap: %s and %s" % (previous, old_n))
        new_n = None if new == "-" else norm(new)
        if new_n == old_n or (new_n is not None and new_n.startswith(old_n + "/")):
            raise UsageError("cannot move %s to itself or inside itself: %s" % (old, new))
        seen.add(old_n)
        pairs.append((old_n, new_n))
    for _, new_n in pairs:
        for other, _ in pairs:
            if new_n is not None and (new_n == other or new_n.startswith(other + "/")):
                raise UsageError("%s would land in %s, which another move takes away: run the two moves one after the "
                                 "other" % (new_n, other))
    return Moves(pairs)


def refuse_moves_into_themselves(root, moves):
    """parse_moves compares names; on a file system that ignores case, docs and Docs/sub still name one folder.
    Refuse a new path inside its own old path, or at or inside another move's old path, as the disk sees them."""
    for old, new in moves.pairs:
        if new is None:
            continue
        parts = new.split("/")
        for count in range(1, len(parts) + 1):
            above = "/".join(parts[:count])
            path = os.path.join(root, above)
            if not os.path.lexists(path):
                break
            for other, _ in moves.pairs:
                if other == old and count == len(parts):
                    continue                    # the move's own path in another case: a change of case only
                if not same_file(path, os.path.join(root, other)):
                    continue
                if other == old:
                    raise UsageError("cannot move %s inside itself: %s is %s on this file system" % (old, above, old))
                raise UsageError("%s would land in %s, which another move takes away (%s is %s on this file system): "
                                 "run the two moves one after the other" % (new, other, above, other))


def git(root, *args):
    try:
        done = subprocess.run(["git"] + list(args), cwd=root, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)
    return done.returncode, done.stdout + done.stderr


def in_git(root):
    code, out = git(root, "rev-parse", "--is-inside-work-tree")
    return code == 0 and out.strip().startswith("true")


def inside(root, rel):
    """True when the folder that holds rel resolves inside the root (symbolic links followed for the folder only)."""
    real_root = os.path.realpath(root)
    folder = os.path.realpath(os.path.dirname(os.path.join(root, rel)))
    return folder == real_root or folder.startswith(real_root + os.sep)


def project_files(root, use_git):
    """Files to read, relative to the root, posix style; symbolic links are left out."""
    found = None
    if use_git:
        code, out = git(root, "ls-files", "--cached", "--others", "--exclude-standard")
        if code == 0:
            found = {line for line in out.splitlines() if line}
    if found is None:
        found = set()
        for folder, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not os.path.islink(os.path.join(folder, d)))
            for name in files:
                found.add(os.path.relpath(os.path.join(folder, name), root).replace(os.sep, "/"))
    return sorted(rel for rel in found if os.path.isfile(os.path.join(root, rel))
                  and not os.path.islink(os.path.join(root, rel)) and inside(root, rel))


def read_text(root, rel):
    path = os.path.join(root, rel)
    if os.path.islink(path):
        return None
    try:
        if os.path.getsize(path) > TEXT_LIMIT:
            return None
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError:
        return None
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8").split("\n")
    except UnicodeDecodeError:
        return None


def is_markdown(rel):
    return rel.lower().endswith(MARKDOWN)


def is_instruction(rel):
    return rel in INSTRUCTION_FILES or rel.startswith(INSTRUCTION_FOLDERS)


def unwrap(target):
    """(path text, offset into the target) for a link target, without CommonMark's angle brackets."""
    if target.startswith("<") and target.endswith(">"):
        return target[1:-1], 1
    return target, 0


def skip_target(target):
    return not target or target.startswith("#") or SCHEME.match(target) is not None or any(c in target for c in "<>{}$*")


def split_target(target):
    match = re.match(r"^([^#?]*)(.*)$", target)
    return match.group(1), match.group(2)


def resolve(rel, path_part):
    """The root-relative path a link written in file `rel` points at, or None when it leaves the root."""
    if path_part.startswith("/"):
        resolved = norm(path_part)
    else:
        resolved = norm(posixpath.join(posixpath.dirname(rel), path_part))
    return None if resolved.split("/")[0] == ".." else resolved


def repoint(rel, path_part, moves):
    """For a relative link in `rel`: ('same' | 'moved' | 'removed', the path part to write)."""
    target = resolve(rel, path_part)
    if target is None:
        return "same", path_part
    status, new_target = moves.lookup(target)
    if status == "removed":
        return "removed", None
    _, home = moves.lookup(rel)
    if home is None or (status == "same" and home == rel):
        return "same", path_part          # a removed file's own links go with it
    if path_part.startswith("/"):
        written = "/" + new_target
    else:
        written = posixpath.relpath(new_target or ".", posixpath.dirname(home) or ".")
    if path_part.endswith("/") and not written.endswith("/"):
        written += "/"
    return ("same" if written == path_part else "moved"), written


def unfenced(lines):
    out, fence = [], None
    for line in lines:
        mark = FENCE.match(line)
        if fence:
            out.append("")
            if mark and mark.group(1) == fence:
                fence = None
        elif mark:
            fence = mark.group(1)
            out.append("")
        else:
            out.append(line)
    return out


def item(rel, number, kind, start, end, old, new, why):
    return {"file": rel, "line": number, "kind": kind, "start": start, "end": end, "old": old, "new": new,
            "why": why, "instruction": is_instruction(rel)}


def merged_into(root, moves):
    """New paths of moves whose old file is gone while the new one exists: content merged by hand."""
    return {new for old, new in moves.pairs if new and not os.path.lexists(os.path.join(root, old))
            and os.path.lexists(os.path.join(root, new))}


def scan_markdown(rel, lines, moves, merged=frozenset()):
    found = []
    for number, line in enumerate(unfenced(lines), 1):
        codes = [(m.start(), m.end(), m.group(2), m.start(2)) for m in CODE_SPAN.finditer(line)]
        taken = [(c[0], c[1]) for c in codes]

        def in_code(position):
            return any(c[0] <= position < c[1] for c in codes)

        def link(start, target, why):
            taken.append((start, start + len(target)))
            path_text, offset = unwrap(target)
            if skip_target(path_text):
                return
            path_part, fragment = split_target(path_text)
            if not path_part:
                return
            status, written = repoint(rel, path_part, moves)
            begin = start + offset
            end = begin + len(path_part)
            if status == "moved":
                found.append(item(rel, number, "REWRITE", begin, end, path_part, written, why))
                target_after = resolve(rel, path_part)
                landing = moves.lookup(target_after)[1] if target_after else None
                if fragment.startswith("#") and landing in merged:
                    found.append(item(rel, number, "DECIDE", begin, end, path_part + fragment, None,
                                      "section %s may not exist in %s, which another file was merged into" % (fragment, landing)))
            elif status == "removed":
                found.append(item(rel, number, "DECIDE", begin, end, path_part, None, why + " to a removed file"))

        for match in LINK.finditer(line):
            if not in_code(match.start()):
                link(match.start(2), match.group(2), "link")
        match = DEFINITION.match(line)
        if match and not in_code(match.start(2)):
            link(match.start(2), match.group(2), "link definition")
        for match in IMPORT.finditer(line):
            if not in_code(match.start()):
                link(match.start(1), match.group(1), "import")
        for _, _, content, begin in codes:
            if " " in content or not content:
                continue
            exact = written_path(rel, number, line, begin, content, moves, "path in backticks", single_ok=True)
            name = re.sub(r":\d+(?:-\d+)?$", "", content[2:] if content.startswith("./") else content)
            if not exact and "/" not in name:
                exact = bare_name(rel, number, begin + content.index(name), name, moves)   # a name relative to its folder?
            found.extend(exact)
        for match in PATH_TOKEN.finditer(line):
            if any(s <= match.start() < e for s, e in taken):
                continue
            token = match.group(1)
            if "/" in token:
                found.extend(written_path(rel, number, line, match.start(1), token + (match.group(2) or ""), moves,
                                          "path in prose", single_ok=False))
            else:
                found.extend(bare_name(rel, number, match.start(1), token, moves))
            taken.append((match.start(), match.end()))
    return found


def written_path(rel, number, line, start, token, moves, why, single_ok):
    """A root-relative path written out (with an optional :line suffix) that names an old path."""
    match = re.fullmatch(r"(\./)?(.+?)(:\d+(?:-\d+)?)?", token)
    prefix, body, suffix = match.group(1) or "", match.group(2), match.group(3) or ""
    if not ("/" in body or (single_ok and re.search(r"\.[A-Za-z0-9]{1,5}$", body))):
        return []
    trailing = "/" if body.endswith("/") else ""
    status, new = moves.lookup(norm(body))
    end = start + len(prefix) + len(body)
    if status == "moved":
        return [item(rel, number, "REWRITE", start + len(prefix), end, body, new + ("/" if trailing and not new.endswith("/") else ""), why)]
    if status == "removed":
        return [item(rel, number, "DECIDE", start + len(prefix), end, body, None, why + " to a removed file")]
    return []


def bare_name(rel, number, start, token, moves):
    """A moved file's name written alone in prose: a person decides what the sentence should say."""
    for old, new in moves.pairs:
        if posixpath.splitext(old)[1] and token == posixpath.basename(old):
            hint = "point it at %s, rewrite the sentence, or keep it" % new if new else "it names a removed file"
            return [item(rel, number, "DECIDE", start, start + len(token), token, None, "names %s in prose; %s" % (token, hint))]
    return []


def scan_other(rel, lines, moves):
    """Settings, CI, hook files and scripts: paths relative to the root; ./ and ../ paths relative to the file too."""
    found = []
    for number, line in enumerate(lines, 1):
        for match in PATH_TOKEN.finditer(line):
            token = match.group(1)
            start, end = match.start(1), match.end(1)
            if not token.startswith("../"):
                prefix = "./" if token.startswith("./") else ""
                status, new = moves.lookup(norm(token))
                if status == "moved":
                    found.append(item(rel, number, "REWRITE", start, end, token, prefix + new, "path"))
                    continue
                if status == "removed":
                    found.append(item(rel, number, "DECIDE", start, end, token, None, "path to a removed file"))
                    continue
            if token.startswith(("./", "../")):
                status, written = repoint(rel, token, moves)
                target_moved = moves.lookup(resolve(rel, token) or "")[0] != "same"
                if status == "moved" and token.startswith("./") and not target_moved:
                    # the file moved and its ./ path did not: relative to the file, or to the folder a tool runs from?
                    found.append(item(rel, number, "DECIDE", start, end, token, None,
                                      "a ./ path in a moved file; relative to the file or to the folder it runs from?"))
                elif status == "moved":
                    if token.startswith("./") and not written.startswith("."):
                        written = "./" + written
                    found.append(item(rel, number, "REWRITE", start, end, token, written, "path relative to this file"))
                elif status == "removed":
                    found.append(item(rel, number, "DECIDE", start, end, token, None, "path relative to this file to a removed file"))
        for old, new in moves.pairs:
            if posixpath.splitext(old)[1] or "/" in old:
                continue
            for match in re.finditer(r"([\"'])%s\1" % re.escape(old), line):
                found.append(item(rel, number, "DECIDE", match.start() + 1, match.end() - 1, old, None,
                                  "the folder name %s alone; check whether it means this folder" % old))
    return found


def missing_relative(root, files):
    """./ and ../ paths in settings and scripts that point at nothing: warnings (they may be built later)."""
    found = []
    for rel in files:
        if is_markdown(rel):
            continue
        lines = read_text(root, rel)
        if lines is None:
            continue
        for number, line in enumerate(lines, 1):
            for match in PATH_TOKEN.finditer(line):
                token = match.group(1)
                if token.startswith(("./", "../")):
                    target = resolve(rel, token)
                    from_root = norm(token) if token.startswith("./") else None
                    if from_root and os.path.lexists(os.path.join(root, from_root)):
                        continue           # a ./ path is often relative to the folder a tool runs from: the root
                    if target is not None and not os.path.lexists(os.path.join(root, target)):
                        found.append({"file": rel, "line": number, "kind": "WARN", "old": token, "new": None,
                                      "why": "a path relative to this file that points at nothing", "instruction": False})
    return found


def record_target(rel, token, moves):
    """The destination of an old path named in a record, including a bare file name."""
    path, _ = split_target(token)
    for candidate in (norm(path), resolve(rel, path)):
        if candidate is not None:
            status, new = moves.lookup(candidate)
            if status != "same":
                return status, new
    for old, new in moves.pairs:
        if path == posixpath.basename(old):
            return ("removed" if new is None else "moved"), new
    return "same", token


def after_moves(moves, names):
    """Each name as it is after the moves (a removed one as it was)."""
    return {moves.lookup(name)[1] or name for name in names}


def scan(root, files, moves, kept=frozenset()):
    items, merged = [], merged_into(root, moves)
    for rel in files:
        if moves.lookup(rel)[0] == "removed":
            continue
        lines = read_text(root, rel)
        if lines is None:
            continue
        found = scan_markdown(rel, lines, moves, merged) if is_markdown(rel) else scan_other(rel, lines, moves)
        if rel in kept:
            seen = set()
            for entry in found:
                key = (entry["line"], entry["start"])
                if key in seen:
                    continue
                seen.add(key)
                if entry["new"] is None:
                    entry["new"] = record_target(rel, entry["old"], moves)[1] or "-"
                entry.update(kind="KEPT", why="kept as a record")
                items.append(entry)
        else:
            items.extend(found)
    return items


def slug(text):
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text).replace("`", "").strip().lower()
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


def anchors(root, rel):
    """The #section names a Markdown file offers: heading slugs (with -1, -2 for repeats) and explicit ids."""
    lines = read_text(root, rel) or []
    found, seen = set(), {}
    for line in unfenced(lines):
        heading = HEADING.match(line)
        if heading:
            base = slug(heading.group(1))
            count = seen.get(base, 0)
            seen[base] = count + 1
            found.add(base if count == 0 else "%s-%d" % (base, count))
        for match in EXPLICIT_ID.finditer(line):
            found.add((match.group(1) or match.group(2)).lower())
    return found


def broken_links(root, files, moves=None, kept=frozenset()):
    """(problems, warnings): links and imports in Markdown that point at nothing, or at a missing #section."""
    problems, warnings, cache = [], [], {}
    for rel in files:
        if not is_markdown(rel):
            continue
        lines = read_text(root, rel)
        if lines is None:
            continue
        for number, line in enumerate(unfenced(lines), 1):
            codes = [(m.start(), m.end()) for m in CODE_SPAN.finditer(line)]
            targets = [m.group(2) for m in LINK.finditer(line) if not any(s <= m.start() < e for s, e in codes)]
            targets += [m.group(1) for m in IMPORT.finditer(line) if not any(s <= m.start() < e for s, e in codes)]
            match = DEFINITION.match(line)
            if match:
                targets.append(match.group(2))
            for target in targets:
                path_text, _ = unwrap(target)
                if skip_target(path_text):
                    continue
                if rel in kept and record_target(rel, path_text, moves)[0] != "same":
                    continue
                path_part, fragment = split_target(path_text)
                resolved = resolve(rel, path_part) if path_part else None
                if resolved is None:
                    continue
                entry = {"file": rel, "line": number, "kind": "BROKEN", "old": path_text, "new": None,
                         "why": "points at nothing", "instruction": is_instruction(rel)}
                if not os.path.exists(os.path.join(root, resolved)):
                    if path_part.startswith("/"):
                        entry.update(kind="WARN", why="a root-absolute link that matches no file; a site route?")
                        warnings.append(entry)
                    else:
                        problems.append(entry)
                elif fragment.startswith("#") and is_markdown(resolved) and os.path.isfile(os.path.join(root, resolved)):
                    if resolved not in cache:
                        cache[resolved] = anchors(root, resolved)
                    if fragment[1:].lower() not in cache[resolved]:
                        entry["why"] = "no section %s in %s" % (fragment, resolved)
                        problems.append(entry)
    return problems, warnings


def same_file(a, b):
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def linked_part(root, rel):
    """The first part of rel, from the root down, that is a symbolic link, or None."""
    parts = rel.split("/")
    for count in range(1, len(parts) + 1):
        part = "/".join(parts[:count])
        if os.path.islink(os.path.join(root, part)):
            return part
    return None


def safe_target(root, rel):
    """A path that can be written: it resolves inside the root and no part of it is a symbolic link."""
    return inside(root, rel) and linked_part(root, rel) is None


def refuse_links(root, path):
    link = linked_part(root, path)
    if link is not None:
        raise UsageError("%s goes through the symbolic link %s; a move never goes through one" % (path, link))


def refuse_blocked_case_steps(root, moves):
    """A folder whose name changes only by case passes through <old>.relink-case (CASE_STEP). Refuse that move, in
    plan and in apply alike, when the free name is taken on disk or another move would land at or inside it. Only a
    file system that ignores case renames by case alone, so the names are compared without case."""
    for old, new in moves.pairs:
        if new is None:
            continue
        source, target = os.path.join(root, old), os.path.join(root, new)
        if not (os.path.isdir(source) and not os.path.islink(source) and os.path.lexists(target)
                and same_file(source, target)):
            continue
        step = old + CASE_STEP
        if os.path.lexists(os.path.join(root, step)):
            raise UsageError("%s is in the way of the change of case of %s" % (step, old))
        folded = step.casefold()
        for other, landing in moves.pairs:
            if landing and (landing.casefold() == folded or landing.casefold().startswith(folded + "/")):
                raise UsageError("%s would move to %s, the free name the change of case of %s passes through: move it "
                                 "elsewhere" % (other, landing, old))


def check_moves(root, moves):
    """Refuse what cannot be done; return the file or folder moves still to run, as [old, new or None]."""
    refuse_blocked_case_steps(root, moves)
    todo = []
    for old, new in moves.pairs:
        for path in (old, new):
            if path and not inside(root, path):
                raise UsageError("%s resolves outside the root through a symbolic link" % path)
        for path in (old, new):
            if path:
                refuse_links(root, path)
        source = os.path.join(root, old)
        old_there = os.path.lexists(source)
        if new is None:
            if old_there:
                todo.append([old, None])
            continue
        target = os.path.join(root, new)
        new_there = os.path.lexists(target)
        if old_there and new_there and same_file(source, target):
            todo.append([old, new])        # a change of case only, on a file system that ignores case
        elif old_there and new_there and os.path.isdir(source) and not os.path.islink(source) and os.path.isdir(target):
            for folder, dirs, files in os.walk(source):
                for name in sorted(dirs + files):
                    if os.path.islink(os.path.join(folder, name)):
                        inner = os.path.relpath(os.path.join(folder, name), source).replace(os.sep, "/")
                        raise UsageError("%s/%s is a symbolic link; a move never goes through one" % (old, inner))
                for name in sorted(files):
                    inner = os.path.relpath(os.path.join(folder, name), source).replace(os.sep, "/")
                    if os.path.lexists(os.path.join(target, inner)):
                        raise RuntimeError("%s/%s and %s/%s both exist: merge them first" % (old, inner, new, inner))
                    todo.append([old + "/" + inner, new + "/" + inner])
        elif old_there and new_there:
            raise RuntimeError("%s and %s both exist: merge the content into %s and remove %s first" % (old, new, new, old))
        elif not old_there and not new_there:
            raise UsageError("neither %s nor %s exists" % (old, new))
        elif old_there:
            todo.append([old, new])
    targets = {}
    for old, new in todo:
        if new is None:
            continue
        if not safe_target(root, new):
            raise UsageError("%s would be written through a symbolic link or outside the root" % new)
        if new in targets:
            raise UsageError("%s and %s would both move to %s" % (targets[new], old, new))
        targets[new] = old
    for new, old in sorted(targets.items()):
        parts = new.split("/")
        for count in range(1, len(parts)):
            above = "/".join(parts[:count])
            if above in targets:
                raise UsageError("%s would move to %s, inside %s where %s moves: run the two moves one after the other"
                                 % (old, new, above, targets[above]))
    return todo


def tracked(root, path):
    code, out = git(root, "ls-files", "--", path)
    return code == 0 and bool(out.strip())


def move_one(root, old, new, use_git):
    source = os.path.join(root, old)
    if new is None:
        if not os.path.lexists(source):
            return
        if not safe_target(root, old):
            raise RuntimeError("%s goes through a symbolic link or outside the root, so it is not removed; the journal "
                               "%s remains: settle the files by hand, then remove it" % (old, journal_path(root, use_git)))
        if use_git and tracked(root, old):
            code, out = git(root, "rm", "-r", "-q", "--", old)
            if code:
                raise RuntimeError("git rm %s failed: %s; the journal %s remains: settle the files by hand, then remove it" %
                                   (old, out.strip(), journal_path(root, use_git)))
        elif os.path.isdir(source) and not os.path.islink(source):
            shutil.rmtree(source)
        else:
            os.remove(source)
        return
    target = os.path.join(root, new)
    if not safe_target(root, new) or not safe_target(root, old):
        raise RuntimeError("%s or %s goes through a symbolic link or outside the root; the journal %s remains: settle "
                           "the files by hand, then remove it" % (old, new, journal_path(root, use_git)))
    source_there, target_there = os.path.lexists(source), os.path.lexists(target)
    step = old + CASE_STEP
    if not source_there and not target_there and os.path.lexists(os.path.join(root, step)):
        if use_git:                        # a folder's change of case stopped between its two steps
            code, out = git(root, "mv", "--", step, new)
            if code:
                raise RuntimeError("git mv %s %s failed: %s; the journal %s remains: settle the files by hand, then "
                                   "remove it" % (step, new, out.strip(), journal_path(root, use_git)))
        else:
            os.rename(os.path.join(root, step), target)
        return
    if not source_there and target_there:
        return                             # done before an interruption: the old path is gone, the new one holds it
    if source_there and target_there and not same_file(source, target):
        raise RuntimeError("%s is taken by something this apply did not move there while %s is still in place; the "
                           "journal %s remains: settle the files by hand, then remove it" % (new, old, journal_path(root, use_git)))
    if not source_there:
        raise RuntimeError("neither %s nor %s exists any more; the journal %s remains: settle the files by hand, then "
                           "remove it" % (old, new, journal_path(root, use_git)))
    if target_there and os.path.basename(source) not in os.listdir(os.path.dirname(source) or root):
        return                             # a change of case, done before an interruption
    os.makedirs(os.path.dirname(target) or root, exist_ok=True)
    if use_git and tracked(root, old):
        steps = [(old, new)]
        if target_there and os.path.isdir(source):
            if os.path.lexists(os.path.join(root, step)):
                raise RuntimeError("%s is in the way of the change of case of %s; the journal %s remains: settle the "
                                   "files by hand, then remove it" % (step, old, journal_path(root, use_git)))
            steps = [(old, step), (step, new)]      # a folder's change of case: through a free name
        for first, second in steps:
            code, out = git(root, "mv", "--", first, second)
            if code:
                raise RuntimeError("git mv %s %s failed: %s; the journal %s remains: settle the files by hand, then "
                                   "remove it" % (first, second, out.strip(), journal_path(root, use_git)))
    else:
        os.rename(source, target)
    folder = os.path.dirname(source)
    while folder != os.path.abspath(root) and os.path.isdir(folder) and not os.listdir(folder):
        os.rmdir(folder)
        folder = os.path.dirname(folder)


def fingerprint(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def entry_hash(path):
    """A file's SHA-256 over its bytes, or link:<target> for a symbolic link, which is never followed."""
    if os.path.islink(path):
        return "link:" + os.readlink(path)
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(BLOCK), b""):
            digest.update(block)
    return digest.hexdigest()


def held(root, rel):
    """What rel holds, never through a symbolic link: {"": hash} for a file or a link, and for a folder
    {inner path: hash} for every file and link inside it (an empty folder holds {})."""
    path = os.path.join(root, rel)
    if os.path.islink(path) or not os.path.isdir(path):
        return {"": entry_hash(path)}
    found = {}
    for folder, dirs, files in os.walk(path):
        for name in files + [d for d in dirs if os.path.islink(os.path.join(folder, d))]:
            full = os.path.join(folder, name)
            found[os.path.relpath(full, path).replace(os.sep, "/")] = entry_hash(full)
    return found


def holds_what_was_moved(root, rel, recorded, contents):
    """True when rel holds what the journal recorded for it, each file as it was or as this apply rewrote it."""
    try:
        now = held(root, rel)
    except OSError:
        return False
    if set(now) != set(recorded):
        return False
    for inner, value in recorded.items():
        if now[inner] == value:
            continue
        path = rel + "/" + inner if inner else rel
        lines = read_text(root, path) if path in contents else None
        if lines is None or "\n".join(lines) != contents[path][1]:
            return False
    return True


def still_to_move(root, todo, contents, journal):
    """The journal's moves not done yet, once every one is checked; nothing moves while one is in doubt.
    Done: the old path is gone, or only its case changed, and the new path holds what this apply moved there.
    Still to do: the old path is there and the new path free, or a file to remove that is as the journal saw it.
    Nothing is hashed or removed through a symbolic link."""
    left, problems = [], []
    for old, new, recorded in todo:
        source = os.path.join(root, old)
        source_there = os.path.lexists(source)
        if new is None:
            if not safe_target(root, old):
                link = linked_part(root, old)
                problems.append("%s goes through %s, so it is not removed"
                                % (old, "the symbolic link " + link if link else "a folder outside the root"))
            elif source_there and holds_what_was_moved(root, old, recorded, contents):
                left.append([old, None])
            elif source_there:
                problems.append("%s changed since the moves were planned, so it is not removed" % old)
            continue
        if not safe_target(root, old) or not safe_target(root, new):
            problems.append("%s or %s goes through a symbolic link or outside the root" % (old, new))
            continue
        target = os.path.join(root, new)
        target_there = os.path.lexists(target)
        if source_there and target_there and same_file(source, target):
            step = old + CASE_STEP
            if os.path.basename(source) not in os.listdir(os.path.dirname(source)):
                if not holds_what_was_moved(root, new, recorded, contents):    # the change of case is made
                    problems.append("%s holds something other than what this apply moved there from %s (another "
                                    "file, or the moved one edited since)" % (new, old))
            elif os.path.isdir(source) and os.path.lexists(os.path.join(root, step)):
                problems.append("%s is in the way of the change of case of %s" % (step, old))
            else:
                left.append([old, new])    # a change of case still to make
        elif source_there and target_there:
            problems.append("%s is taken by something this apply did not move there while %s is still in place"
                            % (new, old))
        elif source_there:
            left.append([old, new])
        elif not target_there and os.path.lexists(os.path.join(root, old + CASE_STEP)):
            if holds_what_was_moved(root, old + CASE_STEP, recorded, contents):
                left.append([old, new])    # a folder's change of case stopped between its two steps
            else:
                problems.append("%s holds something other than what this apply moved there from %s"
                                % (old + CASE_STEP, old))
        elif not target_there:
            problems.append("neither %s nor %s exists any more" % (old, new))
        elif not holds_what_was_moved(root, new, recorded, contents):
            problems.append("%s holds something other than what this apply moved there from %s (another file, or "
                            "the moved one edited since)" % (new, old))
    if problems:
        raise RuntimeError("%s; this run moved nothing; the journal %s remains: settle the files by hand, then "
                           "remove it" % ("; ".join(problems), journal))
    return left


def new_contents(root, items, moves):
    """{path after the moves: [fingerprint of the text before, the text after]}, read before anything moves."""
    by_file = {}
    for entry in items:
        if entry["kind"] == "REWRITE":
            by_file.setdefault(entry["file"], []).append(entry)
    contents = {}
    for rel, entries in by_file.items():
        _, home = moves.lookup(rel)
        lines = read_text(root, rel)
        if lines is None or home is None:
            continue
        before = "\n".join(lines)
        for entry in sorted(entries, key=lambda e: (e["line"], e["start"]), reverse=True):
            line = lines[entry["line"] - 1]
            if line[entry["start"]:entry["end"]] != entry["old"]:
                raise RuntimeError("%s:%d does not hold %s where the scan found it" % (rel, entry["line"], entry["old"]))
            lines[entry["line"] - 1] = line[:entry["start"]] + entry["new"] + line[entry["end"]:]
        contents[home] = [fingerprint(before), "\n".join(lines)]
    return contents


def journal_path(root, use_git):
    if use_git:
        code, out = git(root, "rev-parse", "--absolute-git-dir")
        if code == 0 and out.strip():
            return os.path.join(out.strip(), JOURNAL)
    return os.path.join(root, "." + JOURNAL)


def write_whole(path, text):
    """Replace a file's text whole or not at all: write a temporary sibling, keep the file's permission bits, then
    rename it over the file. A file its owner made read-only is not replaced."""
    if not os.access(path, os.W_OK):
        raise PermissionError(errno.EACCES, "Permission denied", path)
    mode = stat.S_IMODE(os.stat(path).st_mode)
    folder, name = os.path.split(path)
    handle_fd, temporary = tempfile.mkstemp(prefix="." + name + ".", suffix=".relink", dir=folder)
    try:
        with os.fdopen(handle_fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.remove(temporary)
        except OSError:
            pass
        raise


def write_journal(journal, state):
    partial = journal + ".partial"
    with open(partial, "w", encoding="utf-8") as handle:
        json.dump(state, handle)
    os.replace(partial, journal)


def apply(root, moves, use_git, kept=frozenset()):
    journal = journal_path(root, use_git)
    wanted = [[old, new] for old, new in moves.pairs]
    if os.path.exists(journal):
        try:
            with open(journal, encoding="utf-8") as handle:
                state = json.load(handle)
            pending, todo, contents = state["moves"], state["todo"], state["contents"]
        except (ValueError, KeyError, TypeError):
            raise RuntimeError("the journal %s cannot be read; settle the files by hand, remove it, and run apply again" % journal)
        if pending != wanted:
            raise UsageError("an unfinished apply of other moves is recorded in %s: run apply with those moves" % journal)
        if after_moves(moves, state.get("kept", [])) != after_moves(moves, kept):
            raise UsageError("an unfinished apply in %s uses different --keep files: run with the same records" % journal)
        if not isinstance(todo, list) or not all(isinstance(entry, list) and len(entry) == 3
                                                 and isinstance(entry[2], dict) for entry in todo):
            raise RuntimeError("the journal %s was written by an earlier relink.py and records no fingerprints; settle "
                               "the files by hand, remove it, and run apply again" % journal)
    else:
        todo = [[old, new, held(root, old)] for old, new in check_moves(root, moves)]
        contents = new_contents(root, scan(root, project_files(root, use_git), moves, kept), moves)
        write_journal(journal, {"moves": wanted, "kept": sorted(kept), "todo": todo, "contents": contents})
    for old, new in still_to_move(root, todo, contents, journal):
        move_one(root, old, new, use_git)
    edited = []
    for home, (before, after) in sorted(contents.items()):
        path = os.path.join(root, home)
        if not safe_target(root, home):
            continue
        lines = read_text(root, home)
        current = "\n".join(lines) if lines is not None else None
        if current == after:
            continue                       # written before an interruption
        if current is None or fingerprint(current) != before:
            edited.append(home)            # changed since the journal was written: never overwritten
            continue
        write_whole(path, after)
    if edited:
        raise RuntimeError("changed since the moves were planned, so left as they are: %s; rewrite their references by "
                           "hand (relink.py plan lists them), then remove %s" % (", ".join(edited), journal))
    os.remove(journal)


def verify(root, moves, use_git, kept=frozenset()):
    files = project_files(root, use_git)
    problems, warnings = broken_links(root, files, moves, kept)
    warnings += [entry for entry in missing_relative(root, files)
                 if entry["file"] not in kept or record_target(entry["file"], entry["old"], moves)[0] == "same"]
    for entry in scan(root, files, moves, kept):
        if entry["kind"] == "KEPT":
            warnings.append(entry)  # displayed with warnings, but excluded from the decision count
        elif entry["kind"] == "REWRITE":
            entry["kind"], entry["why"] = "STALE", "still names %s" % entry["old"]
            problems.append(entry)
        elif entry["why"].endswith("to a removed file"):
            if entry["why"].startswith(("link", "import")):
                continue   # a link to a removed file is BROKEN already
            entry["kind"], entry["why"] = "STALE", "still names the removed %s" % entry["old"]
            problems.append(entry)
        else:
            entry["kind"] = "WARN"
            warnings.append(entry)
    return problems, warnings


def print_items(items):
    for entry in items:
        detail = entry["old"] if entry["new"] is None else "%s -> %s" % (entry["old"], entry["new"])
        print("%s:%d: %s %s (%s)%s" % (entry["file"], entry["line"], entry["kind"], detail, entry["why"],
                                       " [instruction]" if entry.get("instruction") else ""))


def main(argv):
    parser = argparse.ArgumentParser(description="Move files and keep every reference to them working.")
    parser.add_argument("mode", choices=("plan", "apply", "verify"))
    parser.add_argument("--move", nargs=2, action="append", metavar=("OLD", "NEW"), help="NEW - removes the file")
    parser.add_argument("--keep", action="append", default=[], metavar="FILE",
                        help="record of the moves, left as written; repeat for each record")
    parser.add_argument("--root", default=".")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)
    try:
        if not os.path.isdir(root):
            raise UsageError("no such folder: %s" % args.root)
        moves = parse_moves(args.move)
        if args.mode in ("plan", "apply"):
            refuse_moves_into_themselves(root, moves)
        use_git = in_git(root)
        files = project_files(root, use_git)
        resuming = args.mode == "apply" and os.path.exists(journal_path(root, use_git))
        if args.mode == "plan":
            refuse_blocked_case_steps(root, moves)
        kept = set()
        for value in args.keep:
            rel = norm(value)
            if os.path.isabs(value) or rel.split("/")[0] in ("..", ""):
                raise UsageError("a kept file must stay inside the root: %s" % value)
            if not safe_target(root, rel):
                raise UsageError("kept file is a symbolic link or resolves outside the root: %s" % value)
            if rel not in files:
                given = rel
                rel = next((listed for listed in files
                            if same_file(os.path.join(root, given), os.path.join(root, listed))), None)
                status, moved = moves.lookup(given)
                if rel is None and status == "moved" and (moved in files or resuming):
                    rel = moved                    # moved by an earlier apply, or on its way there (the journal
                                                   # comparison in apply still guards it)
            if rel is None:
                raise UsageError("no such kept file: %s" % value)
            kept.add(rel)
        if args.mode != "verify" and not moves.pairs:
            raise UsageError("name at least one --move OLD NEW")
        if args.mode == "plan":
            items = scan(root, files, moves, kept)
            broken, site = broken_links(root, files, moves, kept)
            if args.format == "json":
                print(json.dumps({"moves": [[o, n] for o, n in moves.pairs], "items": items, "broken": broken,
                                  "warnings": site}, indent=2))
            else:
                print_items(items + broken + site)
                print("%d to rewrite, %d to decide, %d already broken" % (
                    sum(1 for i in items if i["kind"] == "REWRITE"), sum(1 for i in items if i["kind"] == "DECIDE"), len(broken)))
                print("not checked: references from outside the repository and paths built at run time")
            return 0
        if args.mode == "apply":
            apply(root, moves, use_git, kept)
            kept = {moves.lookup(rel)[1] for rel in kept if moves.lookup(rel)[1] is not None}
        problems, warnings = verify(root, moves, use_git, kept)
        print_items(problems + warnings)
        print("%d problem(s), %d to decide" % (len(problems), sum(1 for entry in warnings if entry["kind"] != "KEPT")))
        return 1 if problems else 0
    except UsageError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc))
        return 1
    except OSError as exc:
        print("interrupted: %s; fix the cause, then run apply again with the same moves to finish" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
