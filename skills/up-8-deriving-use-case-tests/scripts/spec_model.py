"""Shared reader for specification files of a spec-driven project.

Parses the requirements catalog, the entity model, use
case specifications and journey test cases into plain objects, and gives every
script one way to report findings. Every skill that ships scripts carries an
identical copy of this module.

All files are read as data. Nothing here writes to a project.

Requires Python 3.9+, standard library only.
"""
import difflib
import glob
import hashlib
import os
import re
import subprocess
import sys
import unicodedata
from typing import NamedTuple, Optional

# the release these copies belong to; hook_gate.py refuses siblings of another release
UPSPEC_VERSION = "1.4.0"

# --- vocabulary -------------------------------------------------------------

# These artifact kinds can support a behavior change in the spec-first guard.
SPEC_KINDS = ("use_case", "test_case", "process", "overview", "requirements", "entity_model")

UC_STATUSES = ("Draft", "Reviewed", "Approved", "Implemented", "Tested", "Done", "Obsolete")
TC_STATUSES = ("Draft", "Reviewed", "Approved", "Automated", "Obsolete")
REQ_PROGRESS = ("Open", "In Progress", "Implemented", "Verified")
REQ_SCOPE = ("Deferred", "Rejected")
# Position of a use case Status in the lifecycle; Obsolete is outside it.
STATUS_RANK = {name: rank for rank, name in enumerate(UC_STATUSES[:-1])}

FIELD_KEYS = {"Use Case ID": "id", "Use Case Name": "name", "Primary Actor": "primary_actor",
              "Secondary Actors": "secondary_actors", "Goal": "goal", "Trigger": "trigger",
              "Status": "status", "Requirements": "requirements",
              "ID": "id", "Priority": "priority", "Process": "process"}
UC_REQUIRED_KEYS = ("id", "name", "primary_actor", "goal", "trigger", "status", "requirements")
TC_REQUIRED_KEYS = ("id", "goal", "priority", "status", "use_cases")
RECORD_REQUIRED_SECTIONS = ("Context", "Decision", "Specification change", "Consequences")
RECORD_OPTIONAL_SECTIONS = ("Sources of new behavior", "Assumptions", "Reproduction", "Urgent path")
RECORD_OUTCOMES = ("1", "2", "3", "4", "5", "6", "7", "migration")
STUB_TEXT = "Not written yet."
ENTITY_TYPES = ("Text", "Number", "Money", "Date", "Date and time", "Yes/No", "Identifier")
RE_REFERENCE = re.compile(r"^Reference to ([A-Z][A-Z0-9_]*)$")
RE_CHOICE = re.compile(r"^Choice of \S.*$")
# EARS: an optional While/Where clause, then an optional When clause or If ... then, then a subject and
# 'shall' with a non-empty response. Clauses may hold commas (the lazy match backtracks to the comma
# that ends the clause); the response's subject may be any noun phrase, not only 'the system'.
RE_EARS = re.compile(r"^(?:(?:while|where)\s+.+?,\s*)?(?:when\s+.+?,\s*|if\s+.+?,\s*then\s+)?"
                     r"(?!(?:when|while|where|if|then)\b)[^,\s][^,]*?\s+shall\s+\S", re.IGNORECASE)
RE_GHERKIN_STEP = re.compile(r"^\s*(Given|When|Then|And|But)\s+(\S.*?)\s*$")
# A comment line that starts with use case ids annotates the next step: "# UC-001", "# UC-001, UC-002",
# "# UC-001 Book Repair". Any other comment line is ignored.
RE_GHERKIN_ANNOTATION = re.compile(r"^\s*#\s*(UC-\d{3}(?:\s*,\s*UC-\d{3})*)\b")


def entity_type_ok(text):
    text = text.strip()
    return text in ENTITY_TYPES or bool(RE_REFERENCE.match(text)) or bool(RE_CHOICE.match(text))


def ears_ok(text):
    return bool(RE_EARS.match(text.strip()))


def _as_text(value):
    return ", ".join(value) if isinstance(value, list) else (value or "")

# Words that mark a decision nobody made. Matched as whole words, case-insensitive.
WEAK_WORDS = (
    "normally", "usually", "quickly", "quick", "fast", "appropriate", "appropriately",
    "adequate", "adequately", "sufficient", "sufficiently", "reasonable", "flexible",
    "user-friendly", "easy", "easily", "intuitive", "seamless", "seamlessly",
    "as needed", "as appropriate", "if possible", "etc.", "and so on", "and/or", "TBD", "should",
)
# Vocabulary of how a system is built. Reported in steps, flows and rules unless
# the entity model defines the word as a business noun.
MECHANISM_TERMS = (
    ("SMTP", r"\bSMTP\b"), ("email server", r"\be-?mail server\b"), ("JWT", r"\bJWT\b"),
    ("token", r"\btokens?\b"), ("bcrypt", r"\bbcrypt\b"), ("hash", r"\bhash(?:es|ed|ing)?\b"),
    ("salt", r"\bsalt(?:ed)?\b"), ("SHA", r"\bSHA-?\d*\b"), ("SQL", r"\bSQL\b"),
    ("SELECT", r"\bSELECT\b"), ("INSERT", r"\bINSERT\b"), ("UPDATE statement", r"\bUPDATE\s+[a-z_]+\s+SET\b"),
    ("HTTP verb", r"\b(?:GET|POST|PUT|PATCH|DELETE)\s+/"), ("HTTP status", r"\bHTTP\s*\d{3}\b"),
    ("endpoint", r"\bendpoints?\b"), ("regex", r"\bregex(?:es)?\b|\bregular expression"),
    ("exception", r"\b[A-Z][A-Za-z]+Exception\b"), ("handler", r"\bon[A-Z][a-zA-Z]+\s+handler\b|\bonClick\b"),
    ("cron", r"\bcron\b"), ("queue", r"\bmessage queue\b"), ("cache", r"\bcach(?:e|ed|ing)\b"),
    ("DTO", r"\bDTOs?\b"), ("table", r"\b(?:database|db)\s+table\b"), ("JSON", r"\bJSON\b"),
)
# Names and figures that come from the implementation, not from the business. A recovered
# specification that keeps them has transcribed the code; the code's value belongs in the
# recovery ledger or in an NFR row.
IMPLEMENTATION_TERMS = (
    ("internal name", r"(?<![\w/.`-])[a-z][a-z0-9]*(?:_[a-z0-9]+)+(?![\w/.`-])"),
    ("code span", r"`[^`\n]+`"),
    ("milliseconds", r"\b\d+\s*(?:ms|milliseconds?)\b"),
)
# Screen mechanics. A use case says what the actor decides, enters and learns.
UI_TERMS = (
    ("click", r"\bclicks?\b"), ("button", r"\bbuttons?\b"), ("dropdown", r"\bdrop-?downs?\b"),
    ("dialog", r"\bdialog(?:ue)?(?: box)?\b"), ("toast", r"\btoasts?\b"), ("checkbox", r"\bcheck-?box(?:es)?\b"),
    ("tab key", r"\bpresses\s+(?:the\s+)?tab\b"), ("modal", r"\bmodals?\b"), ("pixel", r"\bpixels?\b|\b\d+\s*px\b"),
)

RE_UC_ID = re.compile(r"\bUC-\d{3}\b")
RE_TC_ID = re.compile(r"\bTC-\d{3}\b")
RE_REQ_ID = re.compile(r"\b(?:FR|NFR|C)-\d{3}\b")
RE_RULE_CITE = re.compile(r"\b(?:(UC-\d{3})\s+)?(BR-\d{3})\b")
# A citation into another bounded context: billing/UC-003 BR-002, platform/NFR-001.
# The lookbehind keeps file paths such as ../use-cases/UC-004-x.md out.
RE_EXTERNAL = re.compile(r"(?<![\w./-])([a-z][a-z0-9-]*)/((?:UC|TC|FR|NFR|C)-\d{3})(?:\s+(BR-\d{3}))?")
RE_FIELD = re.compile(r"^\*\*(.+?):\*\*\s*(.*?)\s*$")
RE_NUMBERED = re.compile(r"^\s*(\d+)\.\s+(.*\S)\s*$")
RE_BULLET = re.compile(r"^\s*[-*]\s+(.*\S)\s*$")
RE_STEP_REF = re.compile(r"\(steps?\s+(\d+)(?:\s*(?:-|–|to)\s*(\d+))?\)", re.IGNORECASE)
# An alternative flow that branches from a step of another flow: (A2 step 3)
RE_FLOW_STEP_REF = re.compile(r"\((A\d+)\s+steps?\s+(\d+)\)", re.IGNORECASE)
RE_LINK = re.compile(r"\[[^\]\n]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
RE_CONTINUES = re.compile(r"Use case continues at step (\d+)\.?", re.IGNORECASE)
RE_ENDS = re.compile(r"Use case ends\.?", re.IGNORECASE)
RE_FENCE = re.compile(r"^\s*(```|~~~)")
RULES_HEADING = "## Working from specifications"


# --- findings ---------------------------------------------------------------

class Reporter:
    """Collects findings and prints them as path:line: SEVERITY CODE [element]: message."""

    def __init__(self, root="."):
        self.root = os.path.abspath(root)
        self.findings = []

    def add(self, path, line, severity, code, element, message):
        self.findings.append({"path": self._rel(path), "line": int(line or 0), "severity": severity,
                              "code": code, "element": element or "-", "message": message})

    def error(self, path, line, code, element, message):
        self.add(path, line, "ERROR", code, element, message)

    def warn(self, path, line, code, element, message):
        self.add(path, line, "WARN", code, element, message)

    def info(self, path, line, code, element, message):
        self.add(path, line, "INFO", code, element, message)

    def _rel(self, path):
        try:
            return os.path.relpath(os.path.abspath(str(path)), self.root)
        except ValueError:      # different drive on Windows
            return str(path)

    def count(self, severity):
        return sum(1 for f in self.findings if f["severity"] == severity)

    def sorted(self):
        order = {"ERROR": 0, "WARN": 1, "INFO": 2}
        return sorted(self.findings, key=lambda f: (f["path"], f["line"], order[f["severity"]], f["code"]))

    def print_text(self, stream=None):
        stream = stream or sys.stdout
        for f in self.sorted():
            stream.write("%(path)s:%(line)d: %(severity)s %(code)s [%(element)s]: %(message)s\n" % f)
        stream.write("%d errors, %d warnings, %d infos\n" % (self.count("ERROR"), self.count("WARN"), self.count("INFO")))

    def exit_code(self, strict=False):
        """0 when the check ran, whatever it found, an unreadable file included; with strict, 1 on any error or
        warning."""
        if strict and (self.count("ERROR") or self.count("WARN")):
            return 1
        return 0


# --- low-level reading ------------------------------------------------------

def read_lines(path):
    """Return the lines of a text file, or raise OSError with the path in the message."""
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read().split("\n")
    except (OSError, UnicodeDecodeError) as exc:
        exc.spec_path = path
        raise


OLD_FORMAT_EXIT = 5

RE_FM_KEY = re.compile(r"^([a-z][a-z0-9_]*):(?:[ \t]+(.*?))?[ \t]*$")
# YAML's block scalar indicators: a value that starts with one of these runs on below its key.
FM_BLOCK_START = ("|", ">")
FM_REFUSED_START = {"&": "an anchor", "*": "an alias", "!": "a tag", "{": "a mapping",
                    **{start: "a multi-line value" for start in FM_BLOCK_START}}
# What to say instead of a value on several lines, for the keys where more than "write it on one line" helps:
# a goal that does not fit one line is usually two goals; a use case or journey whose
# id cannot be read cannot be identified, so nothing that cites it is checked against it.
FM_ONE_LINE_ADVICE = {
    "goal": "write the goal on one line; a goal that needs more is usually two goals",
    "id": "write the id on one line; until then the file cannot be identified, and what cites it is not checked",
}


def _fm_one_line(key):
    """What to do instead of a value on several lines (FM_ONE_LINE_ADVICE, or the plain advice)."""
    return FM_ONE_LINE_ADVICE.get(key, "write '%s' on one line" % key)


def _fm_comment(raw):
    """Strip a ' #' comment. A quote counts only where a value or a list item starts, so an apostrophe
    inside a plain value (customer's bike) never hides a comment."""
    quote, at_start = None, True
    for index, char in enumerate(raw):
        if quote:
            if char == quote:
                quote, at_start = None, False
            continue
        if char in "\"'" and at_start:
            quote = char
        elif char == "#" and (index == 0 or raw[index - 1] in " \t"):
            return raw[:index].rstrip()
        at_start = char in "[," or (char in " \t" and at_start)
    return raw


def _fm_scalar(raw):
    """(value, problem). A quoted string loses its quotes; a plain one is kept as written."""
    raw = raw.strip()
    if raw and raw[:1] in "\"'":
        quote = raw[0]
        if len(raw) < 2 or raw[-1] != quote or quote in raw[1:-1]:
            return None, "a quote that does not wrap the whole value (no escapes in the subset)"
        return raw[1:-1], None
    if raw[:1] in FM_REFUSED_START:
        return None, "%s is outside the subset" % FM_REFUSED_START[raw[0]]
    if raw and (raw[:1] in "[]" or "]" in raw):
        return None, "a nested list is outside the subset"
    if re.search(r":[ \t]", raw) or raw.endswith(":"):
        return None, "a plain value with ': ' in it; quote it"
    return raw, None


def _fm_value(raw):
    if raw.startswith("["):
        if not raw.endswith("]"):
            return None, "a list must open and close on one line"
        if not raw[1:-1].strip():
            return [], None
        items, current, quote, at_start = [], "", None, True
        for char in raw[1:-1]:
            if quote:
                if char == quote:
                    quote = None
            elif char in "\"'" and at_start:
                quote = char
            elif char in "[]":
                return None, "a nested list is outside the subset"
            elif char == ",":
                items.append(current)
                current, at_start = "", True
                continue
            current += char
            at_start = at_start and char in " \t"
        items.append(current)
        values = []
        for item in items:
            if not item.strip():
                return None, "an empty list item is outside the subset"
            value, problem = _fm_scalar(item)
            if problem:
                return None, problem
            values.append(value)
        return values, None
    return _fm_scalar(raw) if raw else ("", None)


class FrontMatter:
    """One reading of a file's front matter.

    meta maps key -> (value, line); body_start is the 0-based index of the first line after the closing
    '---'; problems lists (line, message), the subset's refusals and then the shape of list and scalar keys;
    refused maps each key refused as a value on several lines to the line of its refusal, which is that key's
    one finding (no "required key ... is missing" beside it)."""

    def __init__(self, meta=None, body_start=0, problems=None, refused=None):
        self.meta = meta if meta is not None else {}
        self.body_start = body_start
        self.problems = problems if problems is not None else []
        self.refused = refused if refused is not None else {}


def front_matter(lines):
    """The front matter of a file's lines, as one FrontMatter."""
    meta, body_start, problems, refused = _read_subset(lines)
    return FrontMatter(meta, body_start, problems + shape_problems(meta), refused)


def read_front_matter(lines):
    """Read the front matter subset of the current formats: (data, body_start, problems), the subset's own
    refusals only (front_matter() adds the shape of the keys and the refused keys)."""
    return _read_subset(lines)[:3]


def _read_subset(lines):
    """(data, body_start, problems, refused).

    data maps key -> (value, line), value a string or a list of strings; body_start is the 0-based index of
    the first line after the closing '---' (0 when there is no front matter); problems lists (line, message).
    The subset: 'key: value', 'key: [a, b]', quoted strings, '#' comments. Nesting, anchors, tags and
    multi-line values are refused, never guessed.

    A value on several lines is one problem, with the advice to write it on one line, and its key is not read:
    a block scalar ('|', '>') at its key's line; a value refused on its key's line for another reason (a quote,
    a tag, ': ') and continued on indented lines, at its key's line too; a plain value continued on indented
    lines, at the first continued line. Its other lines add nothing. refused maps each key refused this way to
    the line of that problem.
    """
    clean = [line.rstrip("\r") for line in lines]
    if clean:
        clean[0] = clean[0].lstrip("﻿")
    if not clean or clean[0].strip() != "---":
        return {}, 0, [], {}
    data, problems, refused = {}, [], {}
    # last_key: the key the next indented line would continue; refused_at: index in problems of its refusal,
    # when its value was refused on its own line.
    last_key, refused_at = None, None
    for index in range(1, len(clean)):
        number, text = index + 1, clean[index]
        stripped = text.strip()
        if stripped == "---":
            return data, index + 1, problems, refused
        if not stripped or stripped.startswith("#"):
            continue
        if text[:1] in " \t":
            if last_key is None:
                problems.append((number, "an indented line: nested or continued values are outside the subset"))
            elif last_key in refused:
                pass
            elif refused_at is not None:
                line, problem = problems[refused_at]
                problems[refused_at] = (line, "%s, and the value continues on an indented line: %s"
                                        % (problem, _fm_one_line(last_key)))
                refused[last_key] = line
            else:
                problems.append((number, "an indented line continues '%s'; nested or continued values are outside "
                                         "the subset: %s" % (last_key, _fm_one_line(last_key))))
                refused[last_key] = number
                data.pop(last_key, None)
            continue
        match = RE_FM_KEY.match(text)
        if not match:
            problems.append((number, "not a 'key: value' line"))
            last_key, refused_at = None, None
            continue
        key, raw = match.group(1), _fm_comment(match.group(2) or "")
        if key in data:
            problems.append((number, "key '%s' appears twice" % key))
            last_key, refused_at = None, None
            continue
        last_key, refused_at = key, None
        value, problem = _fm_value(raw)
        if problem:
            if raw.startswith(FM_BLOCK_START):
                problem = "%s: %s" % (problem, _fm_one_line(key))
                refused[key] = number
            else:
                refused_at = len(problems)
            problems.append((number, problem))
            continue
        data[key] = (value, number)
    problems.append((1, "front matter is not closed with '---'"))
    return data, 0, problems, refused

LIST_KEYS = ("secondary_actors", "requirements", "use_cases")


def shape_problems(meta):
    return [(line, "key '%s' must hold %s" % (key, "a list" if key in LIST_KEYS else "a scalar"))
            for key, (value, line) in meta.items() if isinstance(value, list) != (key in LIST_KEYS)]


def outside_fences(lines):
    """Yield (line number, text) for lines outside fenced code blocks."""
    fenced = False
    for number, line in enumerate(lines, 1):
        if RE_FENCE.match(line):
            fenced = not fenced
            continue
        if not fenced:
            yield number, line


def table_cells(line):
    text = line.strip()
    if not (text.startswith("|") and text.endswith("|")):
        return None
    return [cell.strip() for cell in text[1:-1].split("|")]


def table_separator(cells):
    """Every column needs a Markdown separator; empty cells are invalid."""
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", c) for c in cells)


def read_tables(lines):
    """Return Markdown tables as dicts: {'line', 'header', 'separator', 'rows': [(line, {column: cell}, cell count)]}."""
    tables, current = [], None
    for number, line in outside_fences(lines):
        cells = table_cells(line)
        if cells is None:
            current = None
            continue
        if current is None:
            current = {"line": number, "header": cells, "separator": None, "rows": []}
            tables.append(current)
        elif number == current["line"] + 1 and table_separator(cells):
            current["separator"] = (number, cells)
            continue    # separator row
        else:
            padded = cells + [""] * (len(current["header"]) - len(cells))
            current["rows"].append((number, dict(zip(current["header"], padded)), len(cells)))
    return tables


def sections(lines, level):
    """Split into sections at headings of the given level: [(title, heading line, [(line no, text)])]."""
    marker = "#" * level + " "
    result, current, fenced = [], None, False
    for number, line in enumerate(lines, 1):
        if RE_FENCE.match(line):
            fenced = not fenced
        if not fenced and line.startswith(marker):
            current = (line[len(marker):].strip(), number, [])
            result.append(current)
        elif not fenced and level > 1 and re.match(r"^#{1,%d} " % (level - 1), line):
            current = None
        elif current is not None:
            current[2].append((number, line))
    return result


def split_external(text):
    """Return (text without cross-context citations, [(context, identifier, rule id or None)])."""
    found = [(m.group(1), m.group(2), m.group(3)) for m in RE_EXTERNAL.finditer(text)]
    return (RE_EXTERNAL.sub("", text) if found else text), found


def kebab(name):
    """File-name form of a use case name: lowercase words joined by hyphens, nothing paraphrased."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def word_hits(text, words):
    """Return the words of the list found in text as whole words, case-insensitive."""
    hits = []
    for word in words:
        if re.search(r"(?<![A-Za-z])" + re.escape(word) + r"(?![A-Za-z])", text, re.IGNORECASE):
            hits.append(word)
    return hits


def pattern_hits(text, patterns):
    return [name for name, pattern in patterns if re.search(pattern, text)]


def is_retired(name):
    """A rule or flow that left the use case keeps its identifier and heading: '### BR-004: Retired, moved to UC-022 BR-025'."""
    return bool(re.match(r"retired\b", (name or "").strip(), re.IGNORECASE))


def local_links(lines):
    """Relative link targets in Markdown text: [(line number, target without its #anchor)].

    Web addresses, mail links and links to a heading of the same file are left out."""
    found = []
    for number, line in outside_fences(lines):
        for match in RE_LINK.finditer(line):
            target = match.group(1)
            if re.match(r"[a-z][a-z0-9+.-]*:", target, re.IGNORECASE) or target.startswith("#"):
                continue
            target = target.split("#", 1)[0]
            if target:
                found.append((number, target))
    return found


def _rules_block_text(root) -> tuple[Optional[str], Optional[str]]:
    """The first guideline file carrying the rules heading, and the text after it."""
    for name in ("AGENTS.md", "CLAUDE.md"):
        path = os.path.join(root, name)
        if not os.path.isfile(path):
            continue
        try:
            text = "\n".join(read_lines(path))
        except (OSError, UnicodeDecodeError):
            continue
        if RULES_HEADING in text:
            return name, text.split(RULES_HEADING, 1)[1]
    return None, None


def read_rules_block(root):
    """The spec-first rules block of a project's guideline file: (file name or None, profile or None, skipped words, lowercase).

    AGENTS.md is read before CLAUDE.md; the first file that carries the block wins."""
    name, block = _rules_block_text(root)
    if block is None:
        return None, None, ""
    profile = re.search(r"^\*\*Profile:\*\*\s*(solo|team)\b", block, re.MULTILINE | re.IGNORECASE)
    skipped = re.search(r"^\*\*Skipped:\*\*\s*(.+)$", block, re.MULTILINE | re.IGNORECASE)
    return name, (profile.group(1).lower() if profile else None), (skipped.group(1).lower() if skipped else "")


RE_SPECS_FOLDER = re.compile(r"^\*\*Specs folder:\*\*\s*`?([^`\s]+?)`?\s*$", re.MULTILINE | re.IGNORECASE)


# The integration branch line shared by setup and change-base resolution.
RE_INTEGRATION_BRANCH = re.compile(r"^\*\*Integration branch:\*\*\s*`?([^`\s]+?)`?\s*$", re.MULTILINE | re.IGNORECASE)


def integration_branch(root=".") -> Optional[str]:
    """The integration branch in the first guideline file carrying the rules block, or None."""
    _, block = _rules_block_text(root)
    match = RE_INTEGRATION_BRANCH.search(block) if block is not None else None
    return match.group(1) if match else None


def recorded_docs(root="."):
    """The specification folder the rules block records (**Specs folder:**), or None.

    A folder inside the project, relative to its root (docs, specs, documentation/specs); a path that leaves the
    root, directly or through a symbolic link, is ignored. The first guideline file that carries the rules block
    decides, as for the profile."""
    _, block = _rules_block_text(root)
    match = RE_SPECS_FOLDER.search(block) if block is not None else None
    if not match:
        return None
    folder = match.group(1).replace("\\", "/").rstrip("/")
    parts = folder.split("/")
    real_root = os.path.realpath(root)
    real = os.path.realpath(os.path.join(root, folder))
    if not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", folder) or any(p in (".", "..") for p in parts) \
            or not (real == real_root or real.startswith(real_root + os.sep)) or real == real_root:
        return None
    return folder


def docs_default(root="."):
    """The folder a script reads when no --docs is given: the one the rules block records, else docs."""
    return recorded_docs(root) or "docs"


def project_root(docs_dir):
    """The project's root for a specification folder: the nearest folder above it whose rules block records this
    folder; else the nearest folder above it that holds AGENTS.md, CLAUDE.md or .git; else its parent."""
    docs_abs = os.path.abspath(docs_dir)
    parent = os.path.dirname(docs_abs)
    probe = parent
    while True:
        folder = recorded_docs(probe)
        if folder and os.path.abspath(os.path.join(probe, folder)) == docs_abs:
            return probe
        if os.path.dirname(probe) == probe:
            break
        probe = os.path.dirname(probe)
    probe = parent
    while True:
        if any(os.path.exists(os.path.join(probe, name)) for name in ("AGENTS.md", "CLAUDE.md", ".git")):
            return probe
        if os.path.dirname(probe) == probe:
            return parent
        probe = os.path.dirname(probe)


# --- the A-files, when the project tracks its work in them ---

A_FILES_MARKER = "<!-- hot zone ends -->"
RE_AB_ID = re.compile(r"\bAB-\d{3}\b")
RE_AH_ID = re.compile(r"\bAH-\d{3}\b")
RE_TICKED_PATH = re.compile(r"`([^`\s]+)`")
# The guideline files and the A-files: none of them can be the home an A-file delegates to.
A_FILE_NAMES = ("AGENTS.md", "CLAUDE.md", "ACTIVE.md", "ABILITIES.md", "AHEAD.md", "ATLAS.md")


# How far into AGENTS.md the A-files' check looks for its index: the cap of its hot zone.
A_FILES_INDEX_LINES = 100
TRACKED_A_FILES = ("ACTIVE.md", "ABILITIES.md", "AHEAD.md", "ATLAS.md")


def a_files_listed(agents_lines):
    """The A-files the index of AGENTS.md lists, read as the A-files' check reads it: the rows of the tables in
    its first 100 lines whose first cell is an A-file's name (in backticks, as a link, or after ./); fenced
    blocks are examples. An AGENTS.md with no such row names its files in prose, and every A-file named in
    those lines is listed."""
    lines = agents_lines[:A_FILES_INDEX_LINES]
    found = set()
    for table in read_tables(lines):
        if table["separator"] is None:
            continue
        for _, row, _ in table["rows"]:
            cell = re.sub(r"\]\([^)]*\)", "", row.get(table["header"][0], "")).strip("[]` ")
            found.add(cell[2:] if cell.startswith("./") else cell)
    found &= set(TRACKED_A_FILES)
    if found:
        return found
    prose = "\n".join(line for _, line in outside_fences(lines))
    return {name for name in TRACKED_A_FILES if name in prose}


def a_files_present(root):
    """True when ACTIVE.md at the root holds the hot-zone marker."""
    path = os.path.join(root, "ACTIVE.md")
    try:
        return os.path.isfile(path) and any(line.strip() == A_FILES_MARKER for line in read_lines(path))
    except (OSError, UnicodeDecodeError):
        return False


class OptionalFile(NamedTuple):
    """A file a project may lack. present: it exists; lines: its lines, [] when it is absent or cannot be read."""
    present: bool
    lines: list


def _optional_file(root, name):
    path = os.path.join(root, name)
    if not os.path.isfile(path):
        return OptionalFile(False, [])
    try:
        return OptionalFile(True, read_lines(path))
    except (OSError, UnicodeDecodeError):
        return OptionalFile(True, [])


def _hot_zone(lines):
    for number, line in enumerate(lines):
        if line.strip() == A_FILES_MARKER:
            return lines[:number]
    return lines


def _is_empty(value):
    text = value.strip()
    return not text or text in ("—", "–", "-") or re.match(r"(?i)(none|nothing|n/a)\b", text) is not None


def _field(lines, name):
    pattern = re.compile(r"^\s*-\s*\*\*%s:\*\*\s*(.*?)\s*$" % re.escape(name))
    for _, line in outside_fences(lines):
        match = pattern.match(line)
        if match:
            return "" if _is_empty(match.group(1)) else match.group(1)
    return ""


def a_file_home(root, lines):
    """The tracking file an A-file's hot zone delegates to (**Home:**), or None; lines are the whole A-file."""
    return _home(root, _hot_zone(lines))


def _home(root, lines):
    """The tracking file an A-file delegates to (**Home:** in its hot zone), or None.

    Read as the A-files' tracking check reads it: a home that names an A-file or a guideline file, under any name,
    is no home."""
    for _, line in outside_fences(lines):
        match = re.match(r"^\s*(?:[-*]\s*)?\*\*Home:\*\*\s*(?:\[[^\]]*\]\()?`?([^`)\s]+)", line)
        if match:
            home = match.group(1).rstrip(".,;:") or match.group(1)
            path = os.path.join(root, home)
            for name in A_FILE_NAMES:
                other = os.path.join(root, name)
                try:
                    if os.path.normpath(home) == name or os.path.samefile(path, other):
                        return None
                except OSError:
                    continue
            return home
    return None


def _is_tracking_path(token):
    """Recognize paths by the same rule as the A-files' tracking check."""
    if token.startswith(("http:", "https:", "mailto:", "#")) or any(c in token for c in "<>*{}$"):
        return False
    return "/" in token or re.search(r"\.[A-Za-z0-9]{1,5}$", token) is not None


def _use_case_of(root, link):
    """The use case a Specs link points at: the Use Case ID field of the file, else an identifier in its name."""
    path = os.path.normpath(os.path.join(root, link.split("#", 1)[0]))
    if not os.path.isfile(path):
        return None
    meta, _, _ = read_front_matter(_optional_file(os.path.dirname(path), os.path.basename(path)).lines)
    value = meta.get("id", ("", 0))[0]
    if isinstance(value, str) and RE_UC_ID.fullmatch(value):
        return value
    match = RE_UC_ID.search(os.path.basename(path))
    return match.group(0) if match else None


def _debt(hot):
    """The bullets under `## Debt` in ACTIVE's hot zone, a bullet's continuation lines joined to it (a nested
    sub-bullet is an indented line, so it is folded into its parent); a placeholder bullet is dropped: none, nothing,
    a dash (each alone, trailing punctuation allowed), or text that is only `<...>` placeholders (the template's bullet), punctuation and spaces."""
    bullets, inside = [], False
    for _, line in outside_fences(hot):
        if re.match(r"^##\s", line):
            inside = re.match(r"^##\s+Debt\s*$", line) is not None
            continue
        if not inside:
            continue
        bullet = re.match(r"^[-*]\s+(.*?)\s*$", line)
        if bullet:
            bullets.append(bullet.group(1))
        elif line.strip() and bullets and line[:1] in " \t":
            bullets[-1] += " " + line.strip()
    return [bullet for bullet in bullets
            if not re.fullmatch(r"(?i)(none|nothing|n/a|—|–|-)?[\W_]*", bullet.strip())
            and re.search(r"[^\W_]", re.sub(r"<[^<>]*>", "", bullet))]


def read_tracking(root):
    """What the A-files say about the work, or None when the project does not use them.

    current_work, blocked_by, waiting_on_owner: the text of ACTIVE's fields, '' when empty;
    abilities: {AB id: {name, status, specs (use case ids), links}}, the status from the ability's row in any index
    table of ABILITIES.md, else from an old entry's Status line; abilities_present: whether ABILITIES.md exists
    (without it nothing is said about abilities); next_up: AH ids in order; items: {AH id: [AB ids]} from AHEAD's index;
    debt: the bullets under ACTIVE's `## Debt`, empty when ACTIVE names another home for the current work."""
    if not a_files_present(root):
        return None
    hot = _hot_zone(_optional_file(root, "ACTIVE.md").lines)
    abilities_file = _optional_file(root, "ABILITIES.md")
    abilities_lines = abilities_file.lines
    ahead = _optional_file(root, "AHEAD.md").lines
    active_home = _home(root, hot)
    if active_home:
        hot = []                           # the current work lives in the kept file; ACTIVE's own fields are not it
    tracking = {"current_work": _field(hot, "Current work"), "blocked_by": _field(hot, "Blocked by"),
                "waiting_on_owner": _field(hot, "Waiting on owner"), "debt": _debt(hot), "abilities": {}, "next_up": [], "items": {},
                "abilities_present": abilities_file.present,
                "active_home": active_home, "abilities_home": _home(root, _hot_zone(abilities_lines)),
                "ahead_home": _home(root, _hot_zone(ahead))}

    def ability(identifier, name):
        """The ability's record, made the first time an entry heading or an index row names it."""
        return tracking["abilities"].setdefault(identifier, {"name": name, "status": None, "specs": [], "links": []})

    current = None
    for _, line in outside_fences([] if tracking["abilities_home"] else abilities_lines):
        heading = re.match(r"^###\s+(AB-\d{3})\s*(.*?)\s*$", line)
        if heading:
            current = ability(heading.group(1), heading.group(2))
            continue
        if line.startswith("#"):
            current = None
            continue
        field = RE_FIELD.match(re.sub(r"^\s*[-*]\s*", "", line))
        if current is None or not field:
            continue
        label, value = field.group(1).strip().lower(), field.group(2)
        if label == "status":
            current["status"] = value.strip("` ").lower()
        elif label == "specs":
            current["links"] = list(dict.fromkeys(
                RE_LINK.findall(value) + [token for token in RE_TICKED_PATH.findall(value) if _is_tracking_path(token)]))
            linked = [_use_case_of(root, link) for link in current["links"]]
            current["specs"] = list(dict.fromkeys(RE_UC_ID.findall(value) + [uc for uc in linked if uc]))
    # The status lives in the ability's index row, in any index table of the file; an old entry's Status
    # line read above is the fallback when the row has no status.
    for table in [] if tracking["abilities_home"] else read_tables(abilities_lines):
        if not all(column in table["header"] for column in ("ID", "Ability", "Status")):
            continue
        for _, row, _ in table["rows"]:
            identifier, status = row.get("ID", "").strip(), row.get("Status", "").strip("` ").lower()
            if RE_AB_ID.fullmatch(identifier) and not _is_empty(status):
                ability(identifier, row.get("Ability", "").strip())["status"] = status
    if tracking["ahead_home"]:
        return tracking
    text = "\n".join(_hot_zone(ahead))
    if "## Next up" in text:
        tracking["next_up"] = RE_AH_ID.findall(text.split("## Next up", 1)[1].split("\n## ", 1)[0])
    for table in read_tables(ahead):
        if "ID" in table["header"] and "Ability" in table["header"]:
            for _, row, _ in table["rows"]:
                identifier = row.get("ID", "").strip()
                if RE_AH_ID.fullmatch(identifier):
                    tracking["items"][identifier] = RE_AB_ID.findall(row.get("Ability", ""))
    return tracking


# The Decision values of a recovery change log that make it the alignment backlog. Case, emphasis
# and code marks around them do not matter; text after the colon is the detail.
RE_DECISION = re.compile(r"^[*_`]*(later|in change|aligned|dropped)(?=[*_`\s:]|$)[*_`]*\s*:?\s*(.*)$", re.IGNORECASE)
# Words that fill a Decision or Decided by cell while nothing is decided yet (a template placeholder too).
RE_UNDECIDED = re.compile(r"^(?:$|\[|-$|—$|(?:open|pending|undecided|tbd|to decide)\b)", re.IGNORECASE)
# The change log kind for behavior an old specification claims and the code never implemented.
RE_CLAIM_KIND = re.compile(r"^claimed but not built$", re.IGNORECASE)


def _cell(text):
    """A table cell without the emphasis or code marks around it."""
    return (text or "").strip().strip("*_`").strip()


def decision_of(text):
    """(state, detail) of a change log Decision cell: later, in_change, aligned or dropped with the
    text after the colon; undecided while nothing is decided; settled for any other decision."""
    cell = _cell(text)
    match = RE_DECISION.match(cell)
    if match:
        word, detail = match.group(1).lower(), _cell(match.group(2))
        if word == "in change":
            link = RE_LINK.search(detail)
            return "in_change", (link.group(1) if link else detail.strip("`"))
        return word, detail
    if RE_UNDECIDED.match(cell):
        return "undecided", cell
    return "settled", cell


def _decision_paths(state, detail):
    """The record of an entry in change, the audit reports of an aligned one, else []."""
    if state == "in_change":
        return [detail] if detail else []
    if state != "aligned":
        return []
    return [link or part.strip().strip("`") for part in detail.split(";") if part.strip()
            for link in [(RE_LINK.search(part) or [None, None])[1]]]


def parse_change_log(path):
    """Entries of a recovery change log in file order, [] when there is none. Each entry:
    number, line, kind, use_cases, evidence, decision, decided_by (None without the column),
    state and detail (from decision_of), paths (record or reports), ahead (AH ids, [] without the column)."""
    if not path or not os.path.isfile(path):
        return []
    entries = []
    for table in read_tables(read_lines(path)):
        if not table["header"] or table["header"][0].strip() != "#":
            continue
        for line, row, _ in table["rows"]:
            number = row.get("#", "").strip()
            if not number.isdigit():
                continue
            decision = row.get("Decision", "")
            state, detail = decision_of(decision)
            entries.append({"number": int(number), "line": line, "kind": _cell(row.get("Kind", "")),
                            "use_cases": RE_UC_ID.findall(row.get("Use case", "")), "evidence": row.get("Evidence", ""),
                            "decision": decision.strip(), "decided_by": row.get("Decided by"),
                            "state": state, "detail": detail, "paths": _decision_paths(state, detail),
                            "ahead": RE_AH_ID.findall(row.get("Ahead", ""))})
    return entries


# An audit names the recovery entries it can close on a Change log line; label emphasis is optional.
RE_AUDIT_CHANGE_LOG = re.compile(r"^[*_]*Change log[*_]*:[*_]*(.*)$", re.IGNORECASE)
# Entry citations are whole numbers after #, rather than use case identifiers or prose on other lines.
RE_CHANGE_LOG_NUMBER = re.compile(r"#(\d+)")


# The audit's clean verdicts may include explanations, as in n/a (no UI).
CLEAN_VERDICTS = ("covered", "not applicable", "n/a")


def closure_problems(root, entry):
    """Shared closure check: (severity, code, message) findings for an aligned entry."""
    if entry["state"] != "aligned":
        return []
    problems, named = [], set()
    for target in entry["paths"]:
        full = os.path.join(root, target)
        if not os.path.isfile(full):
            problems.append(("error", "AUDIT_REPORT_MISSING", "%s does not exist under %s" % (target, root)))
            continue
        lines = read_lines(full)
        matrices = [table for table in read_tables(lines)
                    if table["header"] and table["header"][0] == "Unit"
                    and "Verdict" in table["header"] and table["rows"]]
        if not matrices:
            problems.append(("error", "AUDIT_REPORT_INVALID", "%s is not an audit report: no verdict matrix" % target))
            continue
        reported_entries = {int(number) for _, text in outside_fences(lines)
                            for match in [RE_AUDIT_CHANGE_LOG.match(text)] if match
                            for number in RE_CHANGE_LOG_NUMBER.findall(match.group(1))}
        if entry["number"] not in reported_entries:
            problems.append(("error", "AUDIT_REPORT_STALE",
                             "%s does not list change log #%s: it was not written for this change"
                             % (target, entry["number"])))
        head = next((text for _, text in outside_fences(lines) if text.startswith("#")), "")
        named.update(RE_UC_ID.findall(os.path.basename(target)) + RE_UC_ID.findall(head))
        gaps = [row.get("Unit", "?").strip() for table in matrices for _, row, _ in table["rows"]
                if not row.get("Verdict", "").strip().lower().startswith(CLEAN_VERDICTS)]
        if gaps:
            problems.append(("warning", "AUDIT_GAPS",
                             "%s still shows gaps (%s); say why they do not concern this entry" % (target, ", ".join(gaps))))
    missing = [uc for uc in entry["use_cases"] if uc not in named]
    if not entry["paths"] or missing or not entry["use_cases"]:
        problems.append(("error", "ALIGNED_INCOMPLETE",
                         "aligned names an audit report for every use case of the entry; missing: %s"
                         % (", ".join(missing) or "the use case or the report")))
    return problems


# --- locating the artifacts -------------------------------------------------

# Both discovery and classification accept these root file spellings.
DOC_FILES = {"vision": ("vision.md",), "requirements": ("requirements.md", "requirements_catalog.md"),
             "entity_model": ("entity_model.md", "entity-model.md"), "overview": ("use_cases.md",)}
# Classifying removed paths must use the same folder spellings as discovery.
DOC_FOLDERS = {"use_case_dir": ("use_cases", "use-cases", "usecases"),
               "test_case_dir": ("test_cases", "test-cases"), "process_dir": ("processes",),
               "recovery_dir": ("recovery",), "reviews_dir": ("reviews",)}

class Docs:
    """Paths of the specification artifacts under a docs folder, with tolerated older spellings."""

    def __init__(self, docs_dir):
        self.root = docs_dir
        self.notes = []          # (path, message) for tolerated spellings
        for attribute, names in DOC_FILES.items():
            setattr(self, attribute, self._first(*names))
        for attribute, names in DOC_FOLDERS.items():
            setattr(self, attribute, self._first(*names, want_dir=True))

    def _first(self, *names, **options):
        want_dir = options.get("want_dir", False)
        for index, name in enumerate(names):
            path = os.path.join(self.root, name)
            if (os.path.isdir(path) if want_dir else os.path.isfile(path)):
                if index:
                    self.notes.append((path, "older spelling '%s'; the convention is '%s'" % (name, names[0])))
                return path
        return None

    def use_case_files(self):
        return _matching(self.use_case_dir, r"^UC-\d{3}.*\.md$")

    def kind(self, path: str) -> Optional[str]:
        """Classify existing or missing paths by spelling, resolving aliases on both sides."""
        full, root = os.path.realpath(path), os.path.realpath(self.root)
        try:
            if os.path.commonpath([full, root]) != root:
                return None
        except ValueError:  # Paths on different drives cannot share a docs folder.
            return None
        parent, name = os.path.dirname(full), os.path.basename(full)
        if os.path.basename(parent) == "change-records" and name.endswith(".md"):
            return "change_record"
        for kind, attribute, pattern in (("use_case", "use_case_dir", r"UC-\d{3}.*\.md"),
                                          ("test_case", "test_case_dir", r"TC-\d{3}.*\.md"),
                                          ("process", "process_dir", r".*\.bpmn")):
            if re.fullmatch(pattern, name) and any(
                    parent == os.path.realpath(os.path.join(root, spelling)) for spelling in DOC_FOLDERS[attribute]):
                return kind
        for kind, attribute in (("review", "reviews_dir"), ("recovery", "recovery_dir")):
            for spelling in DOC_FOLDERS[attribute]:
                directory = os.path.realpath(os.path.join(root, spelling))
                if os.path.commonpath([full, directory]) == directory:
                    return kind
        for kind, spellings in DOC_FILES.items():
            if any(full == os.path.realpath(os.path.join(root, spelling)) for spelling in spellings):
                return kind
        return "other"

    def test_case_files(self):
        return _matching(self.test_case_dir, r"^TC-\d{3}.*\.md$")

    def change_record_files(self):
        return sorted(glob.glob(os.path.join(self.root, "**", "change-records", "*.md"), recursive=True))

    def process_files(self):
        return _matching(self.process_dir, r".*\.bpmn$")


def _matching(directory, pattern):
    if not directory:
        return []
    return [os.path.join(directory, name) for name in sorted(os.listdir(directory)) if re.match(pattern, name)]


# --- requirements catalog ---------------------------------------------------

class Requirement:
    def __init__(self, rid, row, line, column_count):
        self.id = rid
        self.kind = rid.split("-")[0]
        self.row = row
        self.line = line
        self.column_count = column_count
        self.title = row.get("Title", "")
        self.role = row.get("Role", "")
        self.need = row.get("Need", "")
        self.statement = row.get("Statement", "")
        self.text = self.need or self.statement
        self.status = row.get("Status", "")
        self.priority = row.get("Priority", "")


def parse_requirements(path):
    """Return (requirements, tables). A requirement is any table row whose first cell is an id."""
    lines = read_lines(path)
    requirements, tables = [], read_tables(lines)
    for table in tables:
        if not table["header"] or table["header"][0].strip().upper() != "ID":
            continue
        for line, row, count in table["rows"]:
            rid = row.get(table["header"][0], "")
            if re.fullmatch(r"(?:FR|NFR|C)-\d+", rid):
                requirements.append(Requirement(rid, row, line, count))
    return requirements, tables


# --- entity model -----------------------------------------------------------

class Entity:
    def __init__(self, name, line):
        self.name = name
        self.line = line
        self.description = ""
        self.avoid = []            # words that must not be used for this concept
        self.attributes = []       # (line, row dict)
        self.header = []
        self.header_line = line
        self.separator = None
        self.lifecycle = None      # (line, text)
        self.constraints = []      # (line, text)


class EntityModel:
    def __init__(self):
        self.entities = {}         # name -> Entity
        self.diagram_entities = {} # name -> first line seen in the diagram
        self.relationships = []    # (line, left, right, label)
        self.diagram_attribute_lines = []
        self.has_diagram = False
        self.duplicates = []       # (line, name) of a second section for the same entity

    def nouns(self):
        """Lowercase business nouns defined by the model: entity names and their word forms."""
        nouns = set()
        for name in self.entities:
            words = name.lower().split("_")
            phrase = " ".join(words)
            nouns.update({phrase, phrase + "s"})
            nouns.update(words)
            nouns.update(w + "s" for w in words)
        return nouns


def parse_entity_model(path):
    lines = read_lines(path)
    model = EntityModel()
    in_mermaid = in_block = False
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```mermaid"):
            in_mermaid = True
            continue
        if in_mermaid and stripped.startswith("```"):
            in_mermaid = False
            continue
        if not in_mermaid:
            continue
        if stripped.startswith("erDiagram"):
            model.has_diagram = True
            continue
        if stripped.endswith("{"):
            in_block = True
            model.diagram_entities.setdefault(stripped[:-1].strip().strip('"'), number)
            continue
        if stripped == "}":
            in_block = False
            continue
        if in_block:
            if stripped:
                model.diagram_attribute_lines.append(number)
            continue
        match = re.match(r'^"?([A-Za-z_][\w-]*)"?\s+([|}o][|o.{}-]+[|{o])\s+"?([A-Za-z_][\w-]*)"?\s*(?::\s*(.*))?$', stripped)
        if match:
            left, right, label = match.group(1), match.group(3), (match.group(4) or "").strip().strip('"')
            model.relationships.append((number, left, right, label))
            model.diagram_entities.setdefault(left, number)
            model.diagram_entities.setdefault(right, number)
        elif re.fullmatch(r'"?[A-Za-z_][\w-]*"?', stripped):
            model.diagram_entities.setdefault(stripped.strip('"'), number)
    for title, heading_line, body in sections(lines, 3):
        entity = Entity(title.strip(), heading_line)
        if entity.name in model.entities:
            model.duplicates.append((heading_line, entity.name))
            continue
        model.entities[entity.name] = entity
        table = None
        for number, text in body:
            stripped = text.strip()
            cells = table_cells(text)
            if cells is not None:
                if table is None:
                    table = cells
                    entity.header = cells
                    entity.header_line = number
                elif number == entity.header_line + 1 and table_separator(cells):
                    entity.separator = (number, cells)
                else:
                    entity.attributes.append((number, dict(zip(table, cells + [""] * (len(table) - len(cells)))), len(cells)))
                continue
            field = RE_FIELD.match(stripped)
            if field and field.group(1).lower() in ("not", "avoid"):
                entity.avoid = [w.strip().strip(".") for w in field.group(2).split(",") if w.strip()]
            elif field and field.group(1).lower() == "lifecycle":
                entity.lifecycle = (number, field.group(2))
            elif field and field.group(1).lower() == "constraints":
                entity.constraints.append((number, field.group(2)))
            elif stripped and not entity.description and table is None and not stripped.startswith("**"):
                entity.description = stripped
    return model


# --- use case specification -------------------------------------------------

class Step:
    def __init__(self, number, text, line):
        self.number, self.text, self.line = number, text, line


class Flow:
    def __init__(self, label, name, line):
        self.label, self.name, self.line = label, name, line
        self.trigger = ""
        self.trigger_line = line
        self.trigger_steps = []      # main-scenario step numbers the trigger names
        self.trigger_flow_steps = [] # (flow label, step number) for a flow that branches from another flow
        self.any_time = False
        self.steps = []
        self.ending = None           # ("continues", n) or ("ends", None)
        self.ending_line = line

    @property
    def retired(self):
        return is_retired(self.name)


class Rule:
    def __init__(self, rid, name, line):
        self.id, self.name, self.line = rid, name, line
        self.body = []               # (line, text)
        self.examples = None
        self.examples_blank_before = False

    def text(self):
        return " ".join(text.strip() for _, text in self.body if text.strip() and table_cells(text) is None)

    @property
    def retired(self):
        return is_retired(self.name)


class _WithFrontMatter:
    """A parsed file whose metadata is one FrontMatter (self.front_matter): meta and its problems are read
    from it."""

    @property
    def meta(self):
        return self.front_matter.meta

    @property
    def front_matter_problems(self):
        return self.front_matter.problems


class UseCase(_WithFrontMatter):
    def __init__(self, path):
        self.path = path
        self.title = None
        self.title_line = 0
        self.front_matter = FrontMatter()
        self.is_stub = False
        self.section_lines = {}      # section title -> heading line
        self.preconditions = []      # (line, text)
        self.steps = []
        self.flows = []
        self.flows_placeholder = None  # (line, text) italic statement that no step can fail
        self.success = []
        self.failure = []
        self.rules = []
        self.citations = []          # (line, use case id or None, rule id, where)
        self.external = []           # (line, context, identifier, rule id or None, where): citations into another bounded context
        self.line_count = 0

    def field(self, label):
        return _as_text(self.meta.get(FIELD_KEYS.get(label, label), ("", 0))[0])

    def field_line(self, label):
        return self.meta.get(FIELD_KEYS.get(label, label), ("", 0))[1]

    @property
    def fields(self):
        return {label: (self.field(label), self.field_line(label))
                for label in FIELD_KEYS if FIELD_KEYS[label] in self.meta}

    @property
    def id(self):
        match = RE_UC_ID.search(self.field("Use Case ID"))
        return match.group(0) if match else None

    @property
    def name(self):
        return self.field("Use Case Name") or (self.title or "")

    @property
    def status(self):
        return self.field("Status").strip()

    @property
    def requirement_ids(self):
        return RE_REQ_ID.findall(split_external(self.field("Requirements"))[0])

    @property
    def goal(self):
        return self.field("Goal")

    @property
    def trigger(self):
        return self.field("Trigger")

    @property
    def primary_actors(self):
        value = self.meta.get("primary_actor", ("", 0))[0]
        return [actor.strip() for actor in value.split(",") if actor.strip()] if isinstance(value, str) else []

    @property
    def secondary_actors(self):
        value = self.meta.get("secondary_actors", ([], 0))[0]
        return value if isinstance(value, list) else []

    @property
    def actors(self):
        return self.primary_actors + self.secondary_actors

    def all_step_texts(self):
        """Every step of the main scenario and of the flows: (line, text, where)."""
        items = [(s.line, s.text, "step %d" % s.number) for s in self.steps]
        for flow in self.flows:
            items += [(s.line, s.text, flow.label) for s in flow.steps]
        return items


def parse_use_case(path):
    return parse_use_case_lines(read_lines(path), path)


def parse_use_case_lines(lines, path):
    """Parse a use case from lines already in memory, for example an older revision from git."""
    uc = UseCase(path)
    uc.front_matter = front_matter(lines)
    start = uc.front_matter.body_start
    uc.line_count = len(lines[:-1] if lines and lines[-1] == "" else lines)
    section = sub = None
    flow = rule = None
    for number, line in enumerate(lines[start:], start + 1):
        stripped = line.strip()
        if line.startswith("# "):
            if uc.title is None:
                uc.title = line[2:].strip()
                uc.title_line = number
            continue
        if line.startswith("## "):
            section, sub, flow, rule = line[3:].strip(), None, None, None
            uc.section_lines[section] = number
            continue
        if line.startswith("### "):
            sub = line[4:].strip()
            flow = rule = None
            if section == "Alternative Flows":
                match = re.match(r"^(A\d+)\s*:\s*(.*)$", sub)
                flow = Flow(match.group(1) if match else sub, match.group(2) if match else "", number)
                uc.flows.append(flow)
            elif section == "Business Rules":
                match = re.match(r"^(BR-\d+)\s*:\s*(.*)$", sub)
                rule = Rule(match.group(1) if match else sub, match.group(2) if match else "", number)
                uc.rules.append(rule)
            continue
        if not stripped:
            continue
        field = RE_FIELD.match(stripped)
        numbered = RE_NUMBERED.match(line)
        bullet = RE_BULLET.match(line)
        if section == "Preconditions" and bullet:
            uc.preconditions.append((number, bullet.group(1)))
        elif section == "Main Success Scenario" and numbered:
            uc.steps.append(Step(int(numbered.group(1)), numbered.group(2), number))
        elif section == "Alternative Flows":
            if flow is None:
                if re.fullmatch(r"[_*][^_*].*[_*]", stripped):
                    uc.flows_placeholder = (number, stripped)
                continue
            if field and field.group(1) == "Trigger":
                flow.trigger, flow.trigger_line = field.group(2), number
                for ref in RE_STEP_REF.finditer(field.group(2)):
                    first, last = int(ref.group(1)), int(ref.group(2) or ref.group(1))
                    flow.trigger_steps += list(range(first, last + 1))
                flow.trigger_flow_steps += [(ref.group(1).upper(), int(ref.group(2))) for ref in RE_FLOW_STEP_REF.finditer(field.group(2))]
                flow.any_time = bool(re.search(r"\bat any time\b", field.group(2), re.IGNORECASE))
            elif numbered:
                flow.steps.append(Step(int(numbered.group(1)), numbered.group(2), number))
            text = numbered.group(2) if numbered else stripped
            continues, ends = RE_CONTINUES.search(text), RE_ENDS.search(text)
            if continues:
                flow.ending, flow.ending_line = ("continues", int(continues.group(1))), number
            elif ends:
                flow.ending, flow.ending_line = ("ends", None), number
        elif section == "Postconditions" and bullet:
            target = uc.success if (sub or "").lower().startswith("success") else uc.failure
            target.append((number, bullet.group(1)))
        elif section == "Business Rules" and rule is not None:
            rule.body.append((number, line))
            cells = table_cells(line)
            if cells is not None:
                if rule.examples is None:
                    rule.examples = {"line": number, "header": cells, "separator": None, "rows": []}
                    rule.examples_blank_before = number > 1 and not lines[number - 2].strip()
                elif number == rule.examples["line"] + 1 and table_separator(cells):
                    rule.examples["separator"] = (number, cells)
                else:
                    rule.examples["rows"].append((number, cells))
    cited = uc.all_step_texts() + [(flow.trigger_line, flow.trigger, flow.label) for flow in uc.flows]
    for line_no, text, where in cited:
        local, external = split_external(text)
        uc.external += [(line_no, context, identifier, rule_id, where) for context, identifier, rule_id in external]
        for cite in RE_RULE_CITE.finditer(local):
            uc.citations.append((line_no, cite.group(1), cite.group(2), where))
    value, line_no = uc.fields.get("Requirements", ("", 0))
    uc.external += [(line_no, context, identifier, rule_id, "Requirements") for context, identifier, rule_id in split_external(value)[1]]
    uc.is_stub = any(l.strip() == STUB_TEXT for l in lines[start:]) and "Main Success Scenario" not in uc.section_lines
    return uc


def load_use_cases(docs):
    return [parse_use_case(path) for path in docs.use_case_files()]


def unidentified_use_cases(use_cases):
    """{identifier in the file name: path} for each use case whose id was refused as a value on several lines.

    Its id cannot be read, so the use case is not identified: a citation of the identifier its file name
    carries cannot be judged, and the overview cannot be generated without dropping it. The file name never
    stands in for the id; it only says which citations to leave unjudged."""
    found = {}
    for uc in use_cases:
        if "id" in uc.front_matter.refused:
            match = RE_UC_ID.search(os.path.basename(uc.path))
            found[match.group(0) if match else os.path.basename(uc.path)] = uc.path
    return found


# --- journey test case ------------------------------------------------------

class Scenario:
    def __init__(self, name, line):
        self.name, self.line = name, line
        self.steps = []  # (line, keyword, text, annotated use case ids)
        self.problems = []


class TestCase(_WithFrontMatter):
    def __init__(self, path):
        self.path = path
        self.title = None
        self.front_matter = FrontMatter()
        self.section_lines = {}
        self.roles = []
        self.preconditions = []
        self.postconditions = []
        self.scenarios = []
        self.gherkin_blocks = 0
        self.gherkin_problems = []

    def field(self, label):
        return _as_text(self.meta.get(FIELD_KEYS.get(label, label), ("", 0))[0])

    def field_line(self, label):
        return self.meta.get(FIELD_KEYS.get(label, label), ("", 0))[1]

    @property
    def fields(self):
        return {label: (self.field(label), self.field_line(label))
                for label in FIELD_KEYS if FIELD_KEYS[label] in self.meta}

    @property
    def id(self):
        match = RE_TC_ID.search(self.field("ID"))
        return match.group(0) if match else None

    def use_case_ids(self):
        value = self.meta.get("use_cases", ([], 0))[0]
        return value if isinstance(value, list) else []


def parse_test_case(path):
    lines = read_lines(path)
    tc = TestCase(path)
    tc.front_matter = front_matter(lines)
    start = tc.front_matter.body_start
    section = fence = scenario = None
    gherkin = False
    annotations = []
    for number, line in enumerate(lines[start:], start + 1):
        stripped = line.strip()
        opening = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
        if fence:
            if re.fullmatch(re.escape(fence[0]) + r"{%d,}\s*" % len(fence), stripped):
                fence, gherkin, annotations = None, False, []
                continue
            if not gherkin:
                continue
            if stripped.startswith("Scenario:"):
                scenario = Scenario(stripped[len("Scenario:"):].strip(), number)
                tc.scenarios.append(scenario)
                annotations = []
            elif stripped.startswith("#"):
                match = RE_GHERKIN_ANNOTATION.match(line)
                if match:
                    annotations += RE_UC_ID.findall(match.group(1))
            elif stripped:
                step = RE_GHERKIN_STEP.match(line)
                if step and scenario:
                    scenario.steps.append((number, step.group(1), step.group(2), annotations))
                    annotations = []
                else:
                    message = "'%s' is not a Given, When, Then, And or But step" % stripped
                    (scenario.problems if scenario else tc.gherkin_problems).append((number, message))
            continue
        if opening:
            fence = opening.group(1)
            gherkin = opening.group(2).strip() == "gherkin"
            if gherkin:
                tc.gherkin_blocks += 1
                scenario = None
            continue
        if line.startswith("# ") and tc.title is None:
            tc.title = line[2:].strip()
        elif line.startswith("## "):
            section = line[3:].strip()
            tc.section_lines[section] = number
        else:
            bullet = RE_BULLET.match(line)
            if bullet and section in ("Roles", "Preconditions", "Postconditions"):
                target = {"Roles": tc.roles, "Preconditions": tc.preconditions,
                          "Postconditions": tc.postconditions}[section]
                target.append((number, bullet.group(1)))
    if fence and gherkin:
        tc.gherkin_problems.append((len(lines), "gherkin block is not closed"))
    return tc


# --- coverage units and markers ---------------------------------------------

def coverage_units(uc):
    """The things of one use case that code must realize and tests must exercise."""
    units = [{"unit": "Main", "kind": "scenario", "line": uc.section_lines.get("Main Success Scenario", 0),
              "text": "main success scenario, steps 1-%d" % len(uc.steps)}]
    units += [{"unit": "Step %d" % s.number, "kind": "step", "line": s.line, "text": s.text} for s in uc.steps]
    units += [{"unit": f.label, "kind": "flow", "line": f.line, "text": f.name} for f in uc.flows if not f.retired]
    units += [{"unit": r.id, "kind": "rule", "line": r.line, "text": r.name} for r in uc.rules if not r.retired]
    units += [{"unit": "Pre-%d" % i, "kind": "precondition", "line": line, "text": text}
              for i, (line, text) in enumerate(uc.preconditions, 1)]
    units += [{"unit": "Post-S-%d" % i, "kind": "success postcondition", "line": line, "text": text}
              for i, (line, text) in enumerate(uc.success, 1)]
    units += [{"unit": "Post-F-%d" % i, "kind": "failure postcondition", "line": line, "text": text}
              for i, (line, text) in enumerate(uc.failure, 1)]
    units += [{"unit": rid, "kind": "linked requirement", "line": uc.fields.get("Requirements", ("", 0))[1], "text": rid}
              for rid in uc.requirement_ids if not rid.startswith("FR-")]
    return units


def unit_pattern(unit):
    """Regex that finds a scenario, flow or rule label inside a test name, annotation or comment.

    Main matches 'main'; A1 matches 'A1', 'a1_', 'A1:'; BR-001 matches 'BR-001', 'br001', 'BR_001'.
    Returns None for units that have no label a test could carry (steps, pre- and postconditions).
    """
    if unit == "Main":
        return re.compile(r"(?<![A-Za-z])main(?![A-Za-z])", re.IGNORECASE)
    flow = re.fullmatch(r"A(\d+)", unit)
    if flow:
        return re.compile(r"(?<![A-Za-z0-9])A%s(?!\d)" % flow.group(1), re.IGNORECASE)
    rule = re.fullmatch(r"BR-(\d+)", unit)
    if rule:
        return re.compile(r"(?<![A-Za-z0-9])BR[-_ ]?%s(?!\d)" % rule.group(1), re.IGNORECASE)
    return None


def scan_units(root, uc, suffixes=None):
    """Map unit label -> [(path, line, text)] for files under root that carry the use case id.

    A file belongs to the use case when any line carries its id, plain or compact.
    Inside such a file, a line counts for a unit when it carries the unit's label.
    Lines that carry the qualified form (UC-001 BR-002) count wherever they are.
    """
    files = sorted({path for path, _, _ in find_markers(root, uc.id, suffixes)})

    def sources():
        for path in files:
            try:
                yield path, read_lines(path)
            except (UnicodeDecodeError, OSError):
                continue

    return files, scan_unit_lines(uc, sources())


def scan_unit_lines(uc, sources):
    """Map unit labels to hits in (path, lines) pairs already known to carry the use case id."""
    hits = {}
    labels = ["Main"] + [f.label for f in uc.flows if not f.retired] + [r.id for r in uc.rules if not r.retired]
    patterns = {label: unit_pattern(label) for label in labels}
    for path, lines in sources:
        for number, line in enumerate(lines, 1):
            for label, pattern in patterns.items():
                if pattern is not None and pattern.search(line):
                    hits.setdefault(label, []).append((path, number, line.strip()))
    return hits


def compact_id(identifier):
    """UC-001 -> UC001, the form identifiers take inside class and function names."""
    return identifier.replace("-", "")


# Dependency, build and hidden folders are excluded from every source search.
SOURCE_SKIP = (".git", "node_modules", ".venv", "venv", "dist", "build", "target", "__pycache__")


def git_list(root: str) -> Optional[list[str]]:
    """Tracked and untracked, non-ignored paths relative to root; None without git."""
    code, output = git(["-c", "core.quotePath=false", "ls-files", "-z", "--cached",
                        "--others", "--exclude-standard"], cwd=root)
    return sorted(set(output.rstrip("\0").split("\0")) - {""}) if code == 0 else None


def source_path(path, skip=SOURCE_SKIP):
    """Apply the walk's folder exclusions to a relative git path."""
    return all(part not in skip and not part.startswith(".") for part in path.split("/")[:-1])


def iter_source_files(root, globs=None, skip=SOURCE_SKIP):
    """Yield text files under root, skipping dependency and build folders. globs filters by suffix when given."""
    suffixes = tuple(globs) if globs else None
    listed = git_list(root)
    if listed is not None:
        for relative in listed:
            path = os.path.join(root, relative)
            if source_path(relative, skip) and (not suffixes or relative.endswith(suffixes)) and os.path.isfile(path):
                yield path
        return
    found = []
    for directory, names, files in os.walk(root):
        names[:] = [n for n in names if n not in skip and not n.startswith(".")]
        for name in sorted(files):
            if suffixes and not name.endswith(suffixes):
                continue
            found.append(os.path.join(directory, name))
    yield from sorted(found)


def _marker_patterns(uc_id):
    return tuple(re.compile(r"(?<![A-Za-z0-9])%s(?!\d)" % re.escape(value))
                 for value in (uc_id, compact_id(uc_id)))


def ids_named_by_path(path: str) -> set[str]:
    """Use case ids in a path, with the same boundaries as source markers."""
    return {"UC-" + match.group(1) for match in
            re.finditer(r"(?<![A-Za-z0-9])UC-?(\d{3})(?!\d)", path, re.IGNORECASE)}


def _marker_paths(root, ids, suffixes=None):
    """Narrow one or more marker searches in git, falling back only on errors."""
    args = ["-c", "core.quotePath=false", "grep", "-z", "-l", "-F", "--untracked"]
    for uc_id in sorted(set(ids)):
        args.extend(("-e", uc_id, "-e", compact_id(uc_id)))
    args.append("--")
    args.extend("*" + suffix for suffix in (suffixes or ()))
    code, output = git(args, cwd=root)
    if code == 1:
        return []
    if code == 0:
        return [os.path.join(root, path) for path in sorted(set(output.split("\0")) - {""})
                if source_path(path)]
    return iter_source_files(root, suffixes)


def find_markers(root, uc_id, suffixes=None):
    """Find lines that carry a use case id, in plain (UC-001) or compact (UC001) form.

    Returns [(path, line number, text)]. Binary and unreadable files are skipped.
    """
    plain, compact = _marker_patterns(uc_id)
    hits = []
    for path in _marker_paths(root, [uc_id], suffixes):
        try:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
        except (UnicodeDecodeError, OSError):
            continue
        if "\0" in text or not (plain.search(text) or compact.search(text)):
            continue
        for number, line in enumerate(text.split("\n"), 1):
            if plain.search(line) or compact.search(line):
                hits.append((path, number, line))
    return hits


# Flow and business-rule labels carried by change-record element cells.
UNIT = re.compile(r"\b(A\d+|BR-\d{3})\b")


def record_rows_from(lines, uc_id):
    """Read differences rows with their units, evidence and use case ownership."""
    for table in read_tables(lines):
        header = [h.strip().lower() for h in table["header"]]
        if "element" not in header or not any(h.startswith("today") for h in header):
            continue
        element_col = table["header"][header.index("element")]
        seen_col = next((table["header"][i] for i, h in enumerate(header) if h.startswith("seen")), None)
        rows = []
        for _, row, _ in table["rows"]:
            cell = row.get(element_col, "").strip()
            if not cell or cell.startswith("["):
                continue
            other = [u for u in RE_UC_ID.findall(cell) if u != uc_id]
            mine = True if uc_id in cell else (False if other else None)
            units = [] if mine is False else UNIT.findall(cell)
            rows.append((cell, units, row.get(seen_col, "").strip() if seen_col else None, mine))
        return rows
    return None


def find_change_record(docs, uc_id):
    """The newest record named after the use case or naming it in its metadata or differences."""
    found = []
    for path in docs.change_record_files():
        name = os.path.basename(path)
        named = name == uc_id + ".md" or name.startswith(uc_id + "-")
        if not named:
            named = uc_id in RE_UC_ID.findall(parse_change_record(path).element)
        if not named:
            named = any(mine is True for _, _, _, mine in (record_rows_from(read_lines(path), uc_id) or []))
        if named:
            found.append(path)
    return max(found, key=lambda path: (os.path.getmtime(path), path)) if found else None


# A test file by the names the common test runners use: test_x, x_test, x.test, x-test, x_spec, x.spec, x-spec,
# XTest, XTests, and XIT for a JVM integration test: a CamelCase class name (OrderIT.java), never a name in
# capitals or with underscores (V1__INIT.sql, SUBMIT.py), which is code. One rule for the finish check, the
# spec-first guard, the end-of-turn question and reference search, so that none of them counts a test file as
# code another counts.
TEST_NAME = re.compile(r"(^test_|_test\.|\.test\.|-test\.|_spec\.|\.spec\.|-spec\.|Tests?\.[A-Za-z0-9]+$"
                       r"|^[A-Z][A-Za-z0-9]*[a-z][A-Za-z0-9]*IT\.(?:java|kt|kts|groovy|scala)$)")
# Folders that hold tests or their data, compared in lower case.
TEST_FOLDERS = {"tests", "test", "__tests__", "spec", "specs", "e2e", "testing", "fixtures"}


def is_test_path(path):
    """A test file by its folder or its name."""
    parts = path.replace("\\", "/").split("/")
    return bool(TEST_NAME.search(parts[-1])) or any(part.lower() in TEST_FOLDERS for part in parts[:-1])


# --- the spec-first reading of a change ---------------------------------------
# The spec-first guard and the hook gate's end-of-turn question read a change with this one function.

# Suffixes of source files that can change behavior; documents, data and configuration do not count.
SOURCE_SUFFIXES = (".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".java", ".kt", ".kts", ".go", ".rb",
                   ".php", ".cs", ".rs", ".swift", ".scala", ".c", ".h", ".cc", ".cpp", ".hpp", ".sql", ".vue",
                   ".svelte", ".ex", ".exs", ".dart", ".groovy")
RE_NO_BEHAVIOR_CHANGE = re.compile(r"^\s*(?:[-*>]\s*)?no behaviou?r change\s*:\s*(.*)$", re.IGNORECASE)
# The light path's note: a bug fixed against a clear specification, 'Fixes: UC-012 BR-005'.
# It is read to reconcile, never validated; a 'Fixes:' line that names no use case, such as
# an issue tracker's 'Fixes: #123', is not the note.
RE_FIXES = re.compile(r"^\s*(?:[-*>]\s*)?fixes\s*:\s*(.*)$", re.IGNORECASE)
RE_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
# Five file names fit one line of a message; the rest are counted.
SHOWN_FILES = 5
# Where setup installs the method's own scripts. They are the method's tools, not the project's behavior, and are
# left out on purpose, not because their folder's name happens to be a test folder's.
INSTALLED_SCRIPTS = "tools/specs"


def is_behavior_code(path, docs_rel, patterns=()):
    """A repository-relative path that can change behavior: outside the docs folder and the method's installed
    scripts (INSTALLED_SCRIPTS), not a test, and matching one of the patterns when there are any, else a source file
    by its suffix."""
    import fnmatch
    if path.startswith((docs_rel + "/", INSTALLED_SCRIPTS + "/")) or is_test_path(path):
        return False
    if patterns:
        return any(fnmatch.fnmatch(path, p) for p in patterns)
    return path.endswith(SOURCE_SUFFIXES)


def behavior_declarations(text):
    """(complete, incomplete): the values of 'No behavior change:' lines at the start of a line, outside
    comments. A complete one names a use case or says none."""
    complete, incomplete = [], []
    for line in RE_HTML_COMMENT.sub("", text).splitlines():
        match = RE_NO_BEHAVIOR_CHANGE.match(line)
        if not match:
            continue
        value = match.group(1).strip()
        if RE_UC_ID.search(value) or re.match(r"none\b", value, re.IGNORECASE):
            complete.append(value)
        else:
            incomplete.append(value)
    return complete, incomplete


def fixes_notes(text):
    """The values of 'Fixes:' lines at the start of a line, outside comments, that name a use case."""
    return [match.group(1).strip() for line in RE_HTML_COMMENT.sub("", text).splitlines()
            for match in [RE_FIXES.match(line)] if match and RE_UC_ID.search(match.group(1))]


class SpecFirstReading(NamedTuple):
    """How the spec-first rule reads one change: its behavior files, its specification files, the values of
    its 'No behavior change:' lines and of its 'Fixes:' notes."""
    behavior: list
    specs: list
    complete: list
    incomplete: list
    fixes: tuple = ()

    def code_without_spec(self) -> bool:
        """Behavior code changed with no specification change, no complete declaration and no 'Fixes:' note."""
        return bool(self.behavior) and not self.specs and not self.complete and not self.fixes

    def shown(self) -> str:
        """The behavior files for a message: the first SHOWN_FILES, then a count of the rest."""
        shown = ", ".join(self.behavior[:SHOWN_FILES])
        if len(self.behavior) > SHOWN_FILES:
            shown += " and %d more" % (len(self.behavior) - SHOWN_FILES)
        return shown

    def summary(self, docs_rel) -> str:
        """The one sentence both readers show for code without a specification."""
        return ("%d behavior file(s) changed (%s) with no specification change under %s/, no line "
                "'No behavior change: UC-XXX' and no note 'Fixes: UC-XXX BR-YYY'" % (len(self.behavior), self.shown(), docs_rel))


def read_change(changed, docs_rel, kind, messages, patterns=()):
    """Read a change as the spec-first rule does.

    changed: repository-relative paths; kind: the artifact kind of such a path (Docs.kind); messages: the commit
    messages and descriptions that may carry the declaration; patterns: globs that limit behavior code."""
    behavior = [path for path in changed if is_behavior_code(path, docs_rel, patterns)]
    specs = [path for path in changed if kind(path) in SPEC_KINDS]
    complete, incomplete = behavior_declarations(messages)
    return SpecFirstReading(behavior, specs, complete, incomplete, fixes_notes(messages))


# --- one element of a use case, as the guard check and the finish check name it ---

# The element names of the finish check: a rule, a flow, a main step, a precondition, a success or failure
# postcondition. Steps are written 'Step 4' (the change list's spelling); 'step 4' is accepted.
RE_ELEMENT = re.compile(r"^(UC-\d{3})\s+(?:BR-(\d{3})|A(\d+)|step\s+(\d+)|pre-(\d+)|post-([SF])-(\d+))$", re.IGNORECASE)
# How each kind of element is spelled inside a test name, after spaced(): BR-005 as br005, br_005 or BR-5; A2 as a2
# or a_2 (never "a 2", which is prose); Step 3 as step3 or step_3; Pre-1 as pre1 or precondition_1; Post-S-1 as
# post_s_1, postS1 or postcondition_success_1.
NAME_PREFIXES = {"BR-": "br[-_ ]?", "A": "a[-_]?", "Step ": "step[-_ ]?", "Pre-": "pre(?:condition)?[-_ ]?",
                 "Post-S-": "post(?:condition)?[-_ ]?s(?:uccess)?[-_ ]?",
                 "Post-F-": "post(?:condition)?[-_ ]?f(?:ailure)?[-_ ]?"}


def spaced(text):
    """Lower case, with a separator at every camelCase and letter-digit boundary: testUc012Br005 -> test_uc_012_br_005."""
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", "_", text)
    return re.sub(r"(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])", "_", text).lower()


def _numbered(prefix, number):
    return re.compile(r"(?<![a-z0-9])%s0*%d(?![0-9])" % (prefix, number))


class Element(NamedTuple):
    """One element of a use case: its use case ('UC-012'), its kind (a key of NAME_PREFIXES) and its number."""
    use_case: str
    kind: str
    number: int

    @classmethod
    def parse(cls, text):
        """'UC-012 BR-005', 'UC-012 step 3', 'UC-012 Post-S-1' ...; None when the text names no element."""
        match = RE_ELEMENT.match(" ".join(str(text).split()))
        if not match:
            return None
        uc_id, rule, flow, step, pre, post_kind, post = match.groups()
        kind, number = next((kind, value) for kind, value in (
            ("BR-", rule), ("A", flow), ("Step ", step), ("Pre-", pre),
            ("Post-%s-" % (post_kind or "").upper(), post)) if value)
        return cls(uc_id.upper(), kind, int(number))

    @property
    def name(self):
        """The element in the finish check's spelling: BR-005, A2, Step 3, Pre-1, Post-S-1."""
        return ("BR-%03d" if self.kind == "BR-" else self.kind + "%d") % self.number

    def __str__(self):
        return "%s %s" % (self.use_case, self.name)

    def text(self, uc):
        """The element's text with its whitespace normalized: a rule with its body and its Examples table, a flow
        with its trigger, steps and ending, a step, a precondition, a postcondition. None when the use case has no
        such element."""
        if self.kind == "BR-":
            return next(("\n".join([norm_text(rule.name)] + [norm_text(text) for _, text in rule.body if text.strip()])
                         for rule in uc.rules if rule.id == self.name), None)
        if self.kind == "A":
            return next((flow_text(flow) for flow in uc.flows if flow.label == self.name), None)
        if self.kind == "Step ":
            return next((norm_text(step.text) for step in uc.steps if step.number == self.number), None)
        items = {"Pre-": uc.preconditions, "Post-S-": uc.success, "Post-F-": uc.failure}[self.kind]
        return norm_text(items[self.number - 1][1]) if 0 < self.number <= len(items) else None

    def named_in(self, line):
        """The line holds both the use case and the element, in common spellings."""
        line = spaced(line)
        return bool(_numbered("uc[-_ ]?", int(self.use_case[3:])).search(line)
                    and _numbered(NAME_PREFIXES[self.kind], self.number).search(line))


# Sixteen hex digits (64 bits) tell two versions of one element or one file apart; a collision would need
# billions of versions.
FINGERPRINT_DIGITS = 16


def fingerprint(data):
    """A short fingerprint of a text or of bytes: the first FINGERPRINT_DIGITS of its SHA-256."""
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode("utf-8")).hexdigest()[:FINGERPRINT_DIGITS]


# --- the guard-check log (DIR/reviews/guard-checks.md): guard_check.py writes it, finish_change.py reads it ---

class GuardRow(NamedTuple):
    """One row of the guard-check log. current is False for a row of a table written before upspec 1.3.0 (Unit and
    Verdict columns, no fingerprints)."""
    when: str = ""
    element: str = ""
    file: str = ""
    find: str = ""
    replace: str = ""
    element_fingerprint: str = ""
    file_fingerprint: str = ""
    test: str = ""
    failed_test: str = ""
    verdict: str = ""
    line: int = 0
    current: bool = True


GUARD_LOG_NAME = os.path.join("reviews", "guard-checks.md")
# The log's column for each field of GuardRow that is written.
GUARD_COLUMN_OF = {"when": "When (UTC)", "element": "Element", "file": "File", "find": "Find", "replace": "Replace",
                   "element_fingerprint": "Element fingerprint", "file_fingerprint": "File fingerprint",
                   "test": "Test", "failed_test": "Failed test", "verdict": "Verdict"}
GUARD_WRITTEN = tuple(field for field in GuardRow._fields if field in GUARD_COLUMN_OF)
GUARD_COLUMNS = tuple(GUARD_COLUMN_OF[field] for field in GUARD_WRITTEN)
GUARD_TITLE = ("# Guard checks\n\nOne row per deliberate break, written by guard_check.py. The newest row for an "
               "element is its current result.\n")
GUARD_TABLE = ("\nEach text is kept whole: in a cell, \\\\ is a backslash, \\| a pipe, \\n a line break, \\r a carriage "
               "return, \\t a tab, \\s a space at either end and \\uXXXX any other control character, line separator "
               "or blank at either end. The fingerprints are of the element's text and of the file, when the row was "
               "written.\n\n| %s |\n|%s\n" % (" | ".join(GUARD_COLUMNS), "---|" * len(GUARD_COLUMNS)))
_CELL_NAMED = {"\\": "\\\\", "|": "\\|", "\n": "\\n", "\r": "\\r", "\t": "\\t"}
_CELL_DECODED = {"\\": "\\", "|": "|", "n": "\n", "r": "\r", "t": "\t", "s": " "}


def _escape_char(char, edge):
    """A character as a cell holds it: the named escapes; a space at either end as \\s; a control character, a line
    or paragraph separator, or another blank at either end as \\uXXXX. Every other character is kept as it is."""
    if char in _CELL_NAMED:
        return _CELL_NAMED[char]
    if edge and char == " ":
        return "\\s"
    if unicodedata.category(char) in ("Cc", "Zl", "Zp") or (edge and char.isspace()):
        return "\\u%04x" % ord(char)
    return char


def encode_cell(text):
    """A text as one table cell that keeps it whole: decoded by split_escaped_row to the same text, on one line,
    whatever its characters."""
    text = str(text)
    start = len(text) - len(text.lstrip())
    end = len(text.rstrip())
    return "".join(_escape_char(char, index < start or index >= end) for index, char in enumerate(text))


def _decode_cell(cell):
    out, index = [], 0
    while index < len(cell):
        pair = cell[index:index + 2]
        if pair[:1] == "\\" and pair[1:] == "u" and re.fullmatch(r"[0-9a-fA-F]{4}", cell[index + 2:index + 6]):
            out.append(chr(int(cell[index + 2:index + 6], 16)))
            index += 6
        elif pair[:1] == "\\" and pair[1:] in _CELL_DECODED:
            out.append(_CELL_DECODED[pair[1:]])
            index += 2
        else:
            out.append(cell[index])
            index += 1
    return "".join(out)


def split_escaped_row(line):
    """The cells of a table row written with encode_cell, decoded; None when the line is not a row."""
    text = line.strip()
    if not (text.startswith("|") and text.endswith("|")):
        return None
    cells, current, index = [], [], 1
    while index < len(text):
        char = text[index]
        if char == "\\" and index + 1 < len(text):
            current.append(text[index:index + 2])
            index += 2
            continue
        if char == "|":
            cells.append("".join(current))
            current = []
        else:
            current.append(char)
        index += 1
    if current and "".join(current).strip():
        return None                  # the last pipe was escaped: not a row
    return [_decode_cell(cell.strip()) for cell in cells]


def _element_name(text):
    element = Element.parse(text)
    return str(element) if element else text.strip()


def read_guard_log(path):
    """Every row of the guard-check log in file order, the newest last, as GuardRow. The element is in the finish
    check's spelling when it names one. An empty list when there is no log; OSError or UnicodeDecodeError when it
    cannot be read."""
    if not os.path.isfile(path):
        return []
    rows, header, current = [], None, False
    for number, line in outside_fences(read_lines(path)):
        plain = table_cells(line)
        if plain is None:
            header = None
            continue
        if header is None:
            header, current = plain, tuple(plain) == GUARD_COLUMNS
            continue
        if table_separator(plain):
            continue
        if current:
            cells = split_escaped_row(line)
            if cells is None:
                continue
            row = GuardRow(**dict(zip(GUARD_WRITTEN, cells + [""] * len(GUARD_WRITTEN))), line=number)
        elif "Verdict" in header and ("Unit" in header or "Element" in header):
            named = dict(zip(header, plain + [""] * (len(header) - len(plain))))
            row = GuardRow(when=named.get("When (UTC)", ""), element=named.get("Unit", named.get("Element", "")),
                           file=named.get("File", ""), test=named.get("Test", ""), verdict=named.get("Verdict", ""),
                           line=number, current=False)
        else:
            continue
        rows.append(row._replace(element=_element_name(row.element), verdict=row.verdict.strip()))
    return rows


def append_guard_row(docs_dir, row):
    """Append one GuardRow to the log; a log whose last table is not of GUARD_COLUMNS, an earlier log or one edited
    by hand, gets a new table below it. Returns the log's path; OSError when it cannot be written."""
    path = os.path.join(docs_dir, GUARD_LOG_NAME)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    text = ""
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    last_header = None          # the header of the table the file ends in
    for line in (text.rstrip("\n").split("\n") if text.strip() else []):
        cells = table_cells(line)
        if cells is None:
            last_header = None
        elif last_header is None:
            last_header = tuple(cells)
    head = ""
    if not text.strip():
        head = GUARD_TITLE + GUARD_TABLE
    elif last_header != GUARD_COLUMNS:
        head = ("" if text.endswith("\n") else "\n") + GUARD_TABLE
    elif not text.endswith("\n"):
        head = "\n"
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(head + "| %s |\n" % " | ".join(encode_cell(getattr(row, field)) for field in GUARD_WRITTEN))
    return path


def find_use_case(docs, uc_id):
    """The specification file of a use case, by its file name, in any tolerated spelling of the use case folder;
    None when there is none. The scripts that find a use case's file from its id use this one search; the journey
    check (check_test_case.py) instead matches the id each use case's front matter holds."""
    for spelling in DOC_FOLDERS["use_case_dir"]:
        folder = os.path.join(docs.root, spelling)
        for path in _matching(folder if os.path.isdir(folder) else None, r"^UC-\d{3}.*\.md$"):
            name = os.path.basename(path)
            if name.startswith(uc_id + "-") or name == uc_id + ".md":
                return path
    return None


# --- markers on code nothing calls ------------------------------------------

# A marker right above a definition marks the code that defines the rule, which enforces
# nothing unless something calls it. Keywords of common languages; a method declared without
# a keyword is not recognized, so it is never reported.
DEFINITION = re.compile(
    r"^\s*(?:export\s+)?(?:(?:public|private|protected|internal|static|async|override|final|suspend|default)\s+)*"
    r"(?:def|function\*?|func|fn|fun|sub)\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)"
    r"|^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_]\w*)\s*=\s*(?:async\s+)?(?:function\b|\([^)]*\)\s*=>|[A-Za-z_]\w*\s*=>)")
SKIP_LINE = re.compile(r"^\s*(?:#|//|/\*|\*|--|@|$)")


def marked_definition(lines, index):
    """Name of the function defined right below the marker on lines[index] (0-based), or None."""
    for line in lines[index + 1:index + 4]:
        if SKIP_LINE.match(line):
            continue
        match = DEFINITION.match(line)
        return (match.group(1) or match.group(2)) if match else None
    return None


def count_references(name, texts):
    """How many times the name occurs as a word in the texts, its own definition included."""
    pattern = re.compile(r"(?<![\w$])%s(?![\w$])" % re.escape(name))
    return sum(len(pattern.findall(text)) for text in texts)


# --- comparing two revisions of a use case ------------------------------------

# Steps are paired as "changed" when their texts are at least this similar; below it,
# one is reported as removed and the other as added. 0.6 is difflib's own cutoff
# for "close matches" and keeps reworded steps together without pairing unrelated ones.
SIMILAR_STEPS = 0.6


def norm_text(text):
    return re.sub(r"\s+", " ", text).strip()


def _diff_set(kind, old, new, changes):
    old_set, new_set = [norm_text(t) for _, t in old], [norm_text(t) for _, t in new]
    for text in old_set:
        if text not in new_set:
            changes.append({"change": "removed", "element": kind, "old": text, "new": None})
    for text in new_set:
        if text not in old_set:
            changes.append({"change": "added", "element": kind, "old": None, "new": text})


def _diff_steps(prefix, old, new, changes):
    """Align two step lists by content so that an inserted step does not make every later step 'changed'."""
    old_texts, new_texts = [norm_text(s.text) for s in old], [norm_text(s.text) for s in new]
    matcher = difflib.SequenceMatcher(a=old_texts, b=new_texts, autojunk=False)
    for tag, a1, a2, b1, b2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        removed, added = list(range(a1, a2)), list(range(b1, b2))
        while removed and added:
            i, j = removed[0], added[0]
            if difflib.SequenceMatcher(a=old_texts[i], b=new_texts[j]).ratio() >= SIMILAR_STEPS:
                changes.append({"change": "changed", "element": "%s %d" % (prefix, new[j].number), "old": old_texts[i], "new": new_texts[j]})
                removed.pop(0)
                added.pop(0)
            elif len(removed) > len(added):
                changes.append({"change": "removed", "element": "%s (was %d)" % (prefix, old[i].number), "old": old_texts[i], "new": None})
                removed.pop(0)
            else:
                changes.append({"change": "added", "element": "%s %d" % (prefix, new[j].number), "old": None, "new": new_texts[j]})
                added.pop(0)
        for i in removed:
            changes.append({"change": "removed", "element": "%s (was %d)" % (prefix, old[i].number), "old": old_texts[i], "new": None})
        for j in added:
            changes.append({"change": "added", "element": "%s %d" % (prefix, new[j].number), "old": None, "new": new_texts[j]})


def flow_text(flow):
    ending = "ends" if flow.ending and flow.ending[0] == "ends" else ("continues at step %s" % flow.ending[1] if flow.ending else "no ending")
    return "%s | trigger: %s | %s | %s" % (flow.name, norm_text(flow.trigger), " / ".join(norm_text(s.text) for s in flow.steps), ending)


def compare_use_cases(old, new):
    """Element-by-element changes from one parsed revision of a use case to another:
    [{change: added|changed|removed, element, old, new}]. A removed flow or rule is
    reported as "<label> (was)"."""
    changes = []
    for label in ("Primary Actor", "Secondary Actors", "Goal", "Trigger"):
        if norm_text(old.field(label)) != norm_text(new.field(label)):
            changes.append({"change": "changed", "element": label, "old": old.field(label) or None, "new": new.field(label) or None})
    old_reqs, new_reqs = set(old.requirement_ids), set(new.requirement_ids)
    for rid in sorted(new_reqs - old_reqs):
        changes.append({"change": "added", "element": "Requirements", "old": None, "new": rid})
    for rid in sorted(old_reqs - new_reqs):
        changes.append({"change": "removed", "element": "Requirements", "old": rid, "new": None})
    _diff_set("Precondition", old.preconditions, new.preconditions, changes)
    _diff_steps("Step", old.steps, new.steps, changes)
    old_flows = {norm_text(f.name).lower(): f for f in old.flows}
    new_flows = {norm_text(f.name).lower(): f for f in new.flows}
    by_label_old = {f.label: f for f in old.flows}
    for key, flow in new_flows.items():
        previous = old_flows.get(key)
        if previous is None and flow.label in by_label_old and norm_text(by_label_old[flow.label].name).lower() not in new_flows:
            previous = by_label_old[flow.label]      # same label, renamed condition
            old_flows.pop(norm_text(previous.name).lower(), None)
        elif previous is not None:
            old_flows.pop(key)
        if previous is None:
            changes.append({"change": "added", "element": flow.label, "old": None, "new": flow_text(flow)})
        elif flow_text(previous) != flow_text(flow):
            changes.append({"change": "changed", "element": flow.label, "old": flow_text(previous), "new": flow_text(flow)})
    for flow in old_flows.values():
        changes.append({"change": "removed", "element": "%s (was)" % flow.label, "old": flow_text(flow), "new": None})
    _diff_set("Success postcondition", old.success, new.success, changes)
    _diff_set("Failure postcondition", old.failure, new.failure, changes)
    old_rules = {r.id: r for r in old.rules}
    for rule in new.rules:
        previous = old_rules.pop(rule.id, None)
        text = "%s: %s" % (rule.name, rule.text())
        if previous is None:
            changes.append({"change": "added", "element": rule.id, "old": None, "new": text})
        else:
            before = "%s: %s" % (previous.name, previous.text())
            if norm_text(before) != norm_text(text):
                changes.append({"change": "changed", "element": rule.id, "old": before, "new": text})
    for rule in old_rules.values():
        changes.append({"change": "removed", "element": "%s (was)" % rule.id, "old": "%s: %s" % (rule.name, rule.text()), "new": None})
    return changes


# --- git --------------------------------------------------------------------

def git(args, cwd="."):
    """Run a read-only git command. Returns (exit code, stdout). Never raises for a missing git."""
    try:
        # 60 seconds: history walks on large repositories take seconds, never minutes;
        # a longer wait means git is blocked on a prompt and should be abandoned.
        done = subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="surrogateescape", timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)
    return done.returncode, done.stdout


RE_OLD_UC_FIELD = re.compile(r"^\*\*Use Case ID:\*\*")
RE_OLD_TC_FIELD = re.compile(r"^\*\*ID:\*\*")


def old_formats(docs):
    """Every file still in an earlier format: [(path, line, what)]. Reads nothing else of the project."""
    found = []
    for name in ("use_cases.puml", "use-cases.puml"):
        path = os.path.join(docs.root, name)
        if os.path.isfile(path):
            found.append((path, 1, "PlantUML use case diagram"))
    for name, convention in (("entity-model.md", "entity_model.md"), ("requirements_catalog.md", "requirements.md")):
        path = os.path.join(docs.root, name)
        if os.path.isfile(path):
            found.append((path, 1, "older file name (the convention is %s)" % convention))
    for path in docs.use_case_files():
        hit = next((n for n, line in outside_fences(read_lines(path)) if RE_OLD_UC_FIELD.match(line.strip())), None)
        if hit:
            found.append((path, hit, "bold Overview fields instead of front matter"))
    for path in docs.test_case_files():
        hit = next((n for n, line in outside_fences(read_lines(path)) if line.strip() == "## Flow"), None)
        if hit:
            found.append((path, hit, "journey Flow table"))
    if docs.entity_model:
        hit = next((n for n, line in outside_fences(read_lines(docs.entity_model)) if "Length/Precision" in line), None)
        if hit:
            found.append((docs.entity_model, hit, "database columns in the entity model"))
    if docs.requirements:
        hit = next((n for n, line in outside_fences(read_lines(docs.requirements)) if "User Story" in line), None)
        if hit:
            found.append((docs.requirements, hit, "user story column in the requirements"))
    for path in docs.change_record_files():
        hit = next((n for n, line in outside_fences(read_lines(path)) if line.strip() == "### Classification"), None)
        if hit:
            found.append((path, hit, "the long change record"))
    return found


def stop_if_old(docs, stream=None, report=None, *, strict):
    """Return the exit code the caller stops with, or None when it can go on.

    Earlier formats stop with 5. An unreadable artifact stops the caller too,
    because no caller continues parsing after a read error, and is reported as
    the finding UNREADABLE, to the supplied reporter or to the same stream as
    the migration notice. It then stops with 0, or 1 when strict, as any other
    finding. strict is required and has two states: a check passes its --strict;
    a script that writes or lists passes True, because it cannot do its work
    without the file; a library whose own result is 1 on a problem (the finish
    check, the validator) passes True and leaves --strict to its command line.
    """
    stream = sys.stderr if stream is None else stream
    try:
        found = old_formats(docs)
    except (OSError, UnicodeDecodeError) as exc:
        path = getattr(exc, "spec_path", None) or getattr(exc, "filename", None) or docs.root
        message = "cannot read specification artifacts for old-format recognition: %s" % exc
        if report is not None:
            report.error(path, 0, "UNREADABLE", "-", message)
        else:
            stream.write("%s:0: ERROR UNREADABLE: %s\n" % (path, message))
        return 1 if strict else 0
    if not found:
        return None
    for path, line, what in found:
        stream.write("%s:%d: ERROR OLD_FORMAT: %s\n" % (path, line, what))
    stream.write("This project uses upspec's earlier formats. Migrate it first: the skill up-migrating-spec-formats "
                 "(scripts/migrate_formats.py plan).\n")
    return OLD_FORMAT_EXIT


class ChangeRecord(_WithFrontMatter):
    """The metadata and headings of a short change record."""

    def __init__(self, path):
        self.path = path
        lines = read_lines(path)
        self.front_matter = front_matter(lines)
        start = self.front_matter.body_start
        self.sections = {title: number + start for title, number, _ in sections(lines[start:], 2)}
        self.element = _as_text(self.meta.get("element", ("", 0))[0])
        self.outcome = _as_text(self.meta.get("outcome", ("", 0))[0])


def parse_change_record(path):
    return ChangeRecord(path)


def _metadata_findings(path, fm, required):
    """The front matter problems, and a finding for each required key that is missing or empty, except a key
    already refused as a value on several lines: that refusal is its one finding."""
    found = []
    for line, message in fm.problems:
        found.append((path, line, "FRONT_MATTER", message))
    meta = fm.meta
    for key in required:
        if key in fm.refused:
            continue
        value, line = meta.get(key, ("", 1))
        if key not in meta or (isinstance(value, str) and not value.strip()):
            found.append((path, line, "FRONT_MATTER", "required key '%s' is missing or empty" % key))
    return found


def use_case_format_findings(uc):
    """Current-format findings for one parsed use case, regardless of its file name."""
    def add(path, line, code, message):
        found.append((path, line, code, message))

    found = _metadata_findings(uc.path, uc.front_matter, UC_REQUIRED_KEYS)
    if uc.is_stub:
        if uc.status != "Draft":
            add(uc.path, uc.field_line("Status"), "STUB", "a stub must have status Draft")
        return found
    for rule in uc.rules:
        if rule.retired:
            continue
        examples = rule.examples
        if not examples:
            add(uc.path, rule.line, "EXAMPLES_FORM", "rule needs an Examples table")
            continue
        if not rule.examples_blank_before:
            add(uc.path, examples["line"], "EXAMPLES_FORM",
                "the Examples table needs a blank line before it, or it does not render as a table")
        header = examples["header"]
        if not examples.get("separator"):
            add(uc.path, examples["line"], "EXAMPLES_FORM", "the Examples table needs a separator line (|---|---|)")
        elif len(examples["separator"][1]) != len(header):
            add(uc.path, examples["separator"][0], "EXAMPLES_FORM", "Examples separator must match column count")
        if len(header) < 2 or header[-1] != "result":
            add(uc.path, examples["line"], "EXAMPLES_FORM", "Examples needs input columns followed by result")
        # Two contrasting rows are the minimum evidence for the two
        # sides of a boundary required by the method and design 07.
        if len(examples["rows"]) < 2:
            add(uc.path, examples["line"], "EXAMPLES_FORM", "Examples needs rows on both sides of the boundary")
        for line, cells in examples["rows"]:
            if len(cells) != len(header) or any(not cell.strip() for cell in cells):
                add(uc.path, line, "EXAMPLES_FORM", "Examples row must fill every column")
    return found


def format_findings(docs, kinds=None):
    """All current-format errors as (path, line, code, message).

    The vocabulary and structural checks live here so CLI checks, hooks and
    migration verification report the same errors. Semantic checks stay with
    their callers. Earlier formats must be refused with stop_if_old first.
    """
    selected = set(kinds if kinds is not None else
                   ("use_case", "journey", "requirements", "entity_model", "record"))
    found = []

    def add(path, line, code, message):
        found.append((path, line, code, message))

    def metadata(path, fm, required):
        found.extend(_metadata_findings(path, fm, required))

    if "use_case" in selected:
        if docs.overview:
            metadata(docs.overview, front_matter(read_lines(docs.overview)), ("system",))
        for uc in load_use_cases(docs):
            found.extend(use_case_format_findings(uc))
    if "journey" in selected:
        for path in docs.test_case_files():
            tc = parse_test_case(path)
            metadata(path, tc.front_matter, TC_REQUIRED_KEYS)
            if tc.gherkin_blocks != 1 or len(tc.scenarios) != 1:
                add(path, 1, "GHERKIN_FORM", "journey needs exactly one gherkin block and one Scenario")
            for line, message in tc.gherkin_problems:
                add(path, line, "GHERKIN_FORM", message)
            commented = set()
            # A list of use cases refused as a value on several lines names none; its refusal is the finding.
            listed = None if "use_cases" in tc.front_matter.refused else tc.use_case_ids()
            for scenario in tc.scenarios:
                if not scenario.name or not scenario.steps:
                    add(path, scenario.line, "GHERKIN_FORM", "Scenario needs a name and steps")
                for line, message in scenario.problems:
                    add(path, line, "GHERKIN_FORM", message)
                for line, _, _, ids in scenario.steps:
                    commented.update(ids)
                    for uid in ids:
                        if listed is not None and uid not in listed:
                            add(path, line, "GHERKIN_FORM", "comment names unlisted use case %s" % uid)
            for uid in tc.use_case_ids():
                if uid not in commented:
                    add(path, tc.field_line("use_cases"), "GHERKIN_FORM", "listed use case %s is never commented" % uid)
    if "requirements" in selected and docs.requirements:
        reqs, tables = parse_requirements(docs.requirements)
        req_headers = {
            "FR": ["ID", "Role", "Need", "Priority", "Status"],
            "NFR": ["ID", "Title", "Statement", "Category", "Verification", "Priority", "Status"],
            "C": ["ID", "Title", "Statement", "Category", "Source", "Priority", "Status"],
        }
        for table in tables:
            header = table["header"]
            row_kinds = {row.get(header[0], "").split("-")[0] for _, row, _ in table["rows"]} if header else set()
            kind = next((k for k in req_headers if k in row_kinds), None)
            if not kind and (not header or header[0].strip().upper() != "ID"):
                continue
            if not table.get("separator"):
                add(docs.requirements, table["line"], "TABLE_SEPARATOR", "requirements table needs a separator line (|---|---|)")
            elif len(table["separator"][1]) != len(header):
                add(docs.requirements, table["separator"][0], "TABLE_COLUMNS", "requirements table separator must match column count")
            expected_header = req_headers.get(kind)
            if not expected_header and "Role" in header:
                expected_header = req_headers["FR"]
            elif not expected_header and "Source" in header:
                expected_header = req_headers["C"]
            elif not expected_header and ("Verification" in header or "Statement" in header):
                expected_header = req_headers["NFR"]
            if not expected_header:
                add(docs.requirements, table["line"], "TABLE_COLUMNS", "unknown requirements table columns")
            if expected_header:
                if header != expected_header:
                    add(docs.requirements, table["line"], "TABLE_COLUMNS",
                        "table columns must be: %s" % " | ".join(expected_header))
                for number, row, count in table["rows"]:
                    if count != len(header):
                        add(docs.requirements, number, "TABLE_COLUMNS", "requirements table row must have %d columns" % len(header))
        for req in reqs:
            if req.kind == "FR" and (not req.role.strip() or not req.need.strip()):
                add(docs.requirements, req.line, "NEED_FORM", "functional requirement needs Role and Need")
            elif req.kind in ("NFR", "C") and not ears_ok(req.statement):
                add(docs.requirements, req.line, "NEED_FORM", "Statement must follow an EARS pattern")
    if "entity_model" in selected and docs.entity_model:
        entity_columns = ["Attribute", "Meaning", "Type", "Rules"]
        entities = parse_entity_model(docs.entity_model)
        for entity in entities.entities.values():
            if entity.header:
                if not entity.separator:
                    add(docs.entity_model, entity.header_line, "TABLE_SEPARATOR", "entity table needs a separator line (|---|---|)")
                elif len(entity.separator[1]) != len(entity.header):
                    add(docs.entity_model, entity.separator[0], "TABLE_COLUMNS", "entity table separator must match column count")
                if entity.header != entity_columns:
                    add(docs.entity_model, entity.header_line, "TABLE_COLUMNS",
                        "table columns must be: %s" % " | ".join(entity_columns))
                for line, row, count in entity.attributes:
                    if count != len(entity.header):
                        add(docs.entity_model, line, "TABLE_COLUMNS", "entity table row must have %d columns" % len(entity.header))
            for line, row, _ in entity.attributes:
                text = row.get("Type", "")
                if not entity_type_ok(text):
                    add(docs.entity_model, line, "ENTITY_TYPE", "unknown business type '%s'" % text)
                reference = RE_REFERENCE.fullmatch(text.strip())
                if reference and not any({left, right} == {entity.name, reference.group(1)}
                                         for _, left, right, _ in entities.relationships):
                    add(docs.entity_model, line, "REFERENCE_NO_RELATIONSHIP",
                        "Reference to %s needs a relationship in the diagram" % reference.group(1))
    if "record" in selected:
        for path in docs.change_record_files():
            record = parse_change_record(path)
            required = ("outcome", "element") + (("decided_by",) if record.outcome in ("2", "4", "5", "6") else ())
            metadata(path, record.front_matter, required)
            if record.outcome not in RECORD_OUTCOMES:
                add(path, record.meta.get("outcome", ("", 1))[1], "RECORD_FORM", "unknown outcome '%s'" % record.outcome)
            for title in RECORD_REQUIRED_SECTIONS:
                if title not in record.sections:
                    add(path, 1, "RECORD_FORM", "required section '%s' is missing" % title)
    return found
