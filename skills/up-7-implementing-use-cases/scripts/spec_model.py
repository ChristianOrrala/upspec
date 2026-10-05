"""Shared reader for specification files of a spec-driven project.

Parses the requirements catalog, the entity model, the use case diagram, use
case specifications and journey test cases into plain objects, and gives every
script one way to report findings. Every skill that ships scripts carries an
identical copy of this module.

All files are read as data. Nothing here writes to a project.

Requires Python 3.9+, standard library only.
"""
import difflib
import os
import re
import subprocess
import sys

# --- vocabulary -------------------------------------------------------------

UC_STATUSES = ("Draft", "Reviewed", "Approved", "Implemented", "Tested", "Done", "Obsolete")
TC_STATUSES = ("Draft", "Reviewed", "Approved", "Automated", "Obsolete")
REQ_PROGRESS = ("Open", "In Progress", "Implemented", "Verified")
REQ_SCOPE = ("Deferred", "Rejected")
# Position of a use case Status in the lifecycle; Obsolete is outside it.
STATUS_RANK = {name: rank for rank, name in enumerate(UC_STATUSES[:-1])}

DATA_TYPES = ("Long", "String", "Integer", "Decimal", "Boolean", "Date", "DateTime")

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
        if self.count("ERROR") or (strict and self.count("WARN")):
            return 1
        return 0


# --- low-level reading ------------------------------------------------------

def read_lines(path):
    """Return the lines of a text file, or raise OSError with the path in the message."""
    with open(path, encoding="utf-8") as handle:
        return handle.read().split("\n")


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


def read_tables(lines):
    """Return Markdown tables as dicts: {'line', 'header', 'rows': [(line, {column: cell}, cell count)]}."""
    tables, current = [], None
    for number, line in outside_fences(lines):
        cells = table_cells(line)
        if cells is None:
            current = None
            continue
        if current is None:
            current = {"line": number, "header": cells, "rows": []}
            tables.append(current)
        elif all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c) and not current["rows"]:
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


def read_rules_block(root):
    """The spec-first rules block of a project's guideline file: (file name or None, profile or None, skipped words, lowercase).

    AGENTS.md is read before CLAUDE.md; the first file that carries the block wins."""
    for name in ("AGENTS.md", "CLAUDE.md"):
        path = os.path.join(root, name)
        if not os.path.isfile(path):
            continue
        try:
            text = "\n".join(read_lines(path))
        except (OSError, UnicodeDecodeError):
            continue
        if RULES_HEADING not in text:
            continue
        block = text.split(RULES_HEADING, 1)[1]
        profile = re.search(r"^\*\*Profile:\*\*\s*(solo|team)\b", block, re.MULTILINE | re.IGNORECASE)
        skipped = re.search(r"^\*\*Skipped:\*\*\s*(.+)$", block, re.MULTILINE | re.IGNORECASE)
        return name, (profile.group(1).lower() if profile else None), (skipped.group(1).lower() if skipped else "")
    return None, None, ""


RE_SPECS_FOLDER = re.compile(r"^\*\*Specs folder:\*\*\s*`?([^`\s]+?)`?\s*$", re.MULTILINE | re.IGNORECASE)


def recorded_docs(root="."):
    """The specification folder the rules block records (**Specs folder:**), or None.

    A folder inside the project, relative to its root (docs, specs, documentation/specs); a path that leaves the
    root, directly or through a symbolic link, is ignored. The first guideline file that carries the rules block
    decides, as for the profile."""
    for name in ("AGENTS.md", "CLAUDE.md"):
        path = os.path.join(root, name)
        if not os.path.isfile(path):
            continue
        try:
            text = "\n".join(read_lines(path))
        except (OSError, UnicodeDecodeError):
            continue
        if RULES_HEADING not in text:
            continue
        match = RE_SPECS_FOLDER.search(text.split(RULES_HEADING, 1)[1])
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
    return None


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


def a_files_present(root):
    """True when ACTIVE.md at the root holds the hot-zone marker."""
    path = os.path.join(root, "ACTIVE.md")
    try:
        return os.path.isfile(path) and any(line.strip() == A_FILES_MARKER for line in read_lines(path))
    except (OSError, UnicodeDecodeError):
        return False


def _optional_lines(root, name):
    path = os.path.join(root, name)
    try:
        return read_lines(path) if os.path.isfile(path) else []
    except (OSError, UnicodeDecodeError):
        return []


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
    for line in _optional_lines(os.path.dirname(path), os.path.basename(path))[:20]:
        match = re.match(r"^\*\*Use Case ID:\*\*\s*(UC-\d{3})", line)
        if match:
            return match.group(1)
    match = RE_UC_ID.search(os.path.basename(path))
    return match.group(0) if match else None


def read_tracking(root):
    """What the A-files say about the work, or None when the project does not use them.

    current_work, blocked_by, waiting_on_owner: the text of ACTIVE's fields, '' when empty;
    abilities: {AB id: {name, status, specs (use case ids), links}}; next_up: AH ids in order;
    items: {AH id: [AB ids]} from AHEAD's index."""
    if not a_files_present(root):
        return None
    hot = _hot_zone(_optional_lines(root, "ACTIVE.md"))
    abilities_lines = _optional_lines(root, "ABILITIES.md")
    ahead = _optional_lines(root, "AHEAD.md")
    active_home = _home(root, hot)
    if active_home:
        hot = []                           # the current work lives in the kept file; ACTIVE's own fields are not it
    tracking = {"current_work": _field(hot, "Current work"), "blocked_by": _field(hot, "Blocked by"),
                "waiting_on_owner": _field(hot, "Waiting on owner"), "abilities": {}, "next_up": [], "items": {},
                "active_home": active_home, "abilities_home": _home(root, _hot_zone(abilities_lines)),
                "ahead_home": _home(root, _hot_zone(ahead))}
    current = None
    for _, line in outside_fences([] if tracking["abilities_home"] else abilities_lines):
        heading = re.match(r"^###\s+(AB-\d{3})\s*(.*?)\s*$", line)
        if heading:
            current = tracking["abilities"].setdefault(heading.group(1), {"name": heading.group(2), "status": None,
                                                                         "specs": [], "links": []})
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


# --- locating the artifacts -------------------------------------------------

class Docs:
    """Paths of the specification artifacts under a docs folder, with tolerated older spellings."""

    def __init__(self, docs_dir):
        self.root = docs_dir
        self.notes = []          # (path, message) for tolerated spellings
        self.vision = self._first("vision.md")
        self.requirements = self._first("requirements.md", "requirements_catalog.md")
        self.entity_model = self._first("entity_model.md", "entity-model.md")
        self.diagram = self._first("use_cases.puml", "use-cases.puml")
        self.use_case_dir = self._first("use_cases", "use-cases", "usecases", want_dir=True)
        self.test_case_dir = self._first("test_cases", "test-cases", want_dir=True)
        self.process_dir = self._first("processes", want_dir=True)
        self.recovery_dir = self._first("recovery", want_dir=True)
        self.reviews_dir = self._first("reviews", want_dir=True)

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

    def test_case_files(self):
        return _matching(self.test_case_dir, r"^TC-\d{3}.*\.md$")

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
        self.text = row.get("User Story") or row.get("Requirement") or row.get("Constraint") or row.get("Description", "")
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
                elif not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
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


# --- use case diagram -------------------------------------------------------

class Diagram:
    def __init__(self):
        self.system = None
        self.actors = {}       # alias -> (name, line)
        self.use_cases = {}    # id -> (name, alias, line)
        self.aliases = {}      # alias -> id
        self.links = []        # (line, left alias, right alias, arrow)
        self.bad_labels = []   # (line, text) use case declarations without the id-and-name label
        self.duplicates = []   # (line, id) of a second declaration of the same use case id
        self.has_start = self.has_end = False


def parse_diagram(path):
    lines = read_lines(path)
    diagram = Diagram()
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("@startuml"):
            diagram.has_start = True
        elif stripped.startswith("@enduml"):
            diagram.has_end = True
        actor = re.match(r'^actor\s+"?([^"]+?)"?\s+as\s+(\w+)\s*$', stripped) or re.match(r'^actor\s+(\w+)\s*$', stripped)
        if actor:
            alias = actor.group(2) if actor.lastindex == 2 else actor.group(1)
            diagram.actors[alias] = (actor.group(1), number)
            continue
        box = re.match(r'^(?:rectangle|package)\s+"?([^"{]+?)"?\s*\{', stripped)
        if box:
            diagram.system = box.group(1).strip()
            continue
        use_case = re.match(r'^usecase\s+"([^"]*)"\s+as\s+(\w+)', stripped)
        if use_case:
            label = use_case.group(1)
            match = re.match(r"^(UC-\d+)\\n(.+)$", label)
            if match:
                if match.group(1) in diagram.use_cases:
                    diagram.duplicates.append((number, match.group(1)))
                    continue
                diagram.use_cases[match.group(1)] = (match.group(2).strip(), use_case.group(2), number)
                diagram.aliases[use_case.group(2)] = match.group(1)
            else:
                diagram.bad_labels.append((number, label))
            continue
        link = re.match(r"^(\w+)\s+([.<|o*-]+>?|<?[.|-]+)\s+(\w+)(?:\s*:.*)?$", stripped)
        if link and ("-" in link.group(2) or "." in link.group(2)):
            diagram.links.append((number, link.group(1), link.group(3), link.group(2)))
    return diagram


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

    def text(self):
        return " ".join(text.strip() for _, text in self.body if text.strip())

    @property
    def retired(self):
        return is_retired(self.name)


class UseCase:
    def __init__(self, path):
        self.path = path
        self.title = None
        self.title_line = 0
        self.fields = {}             # label -> (value, line)
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
        return self.fields.get(label, ("", 0))[0]

    @property
    def id(self):
        match = RE_UC_ID.search(self.field("Use Case ID"))
        return match.group(0) if match else None

    @property
    def name(self):
        return self.field("Use Case Name") or (self.title or "")

    @property
    def status(self):
        return self.field("Status").split("|")[0].strip()

    @property
    def requirement_ids(self):
        return RE_REQ_ID.findall(split_external(self.field("Requirements"))[0])

    @property
    def actors(self):
        names = []
        for label in ("Primary Actor", "Secondary Actors"):
            names += [a.strip() for a in self.field(label).split(",") if a.strip()]
        return names

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
    uc.line_count = len(lines[:-1] if lines and lines[-1] == "" else lines)
    section = sub = None
    flow = rule = None
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if line.startswith("# "):
            if uc.title is None:
                uc.title = re.sub(r"^Use Case:\s*", "", line[2:].strip())
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
        if section == "Overview" and field:
            uc.fields[field.group(1)] = (field.group(2), number)
        elif section == "Preconditions" and bullet:
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
    cited = uc.all_step_texts() + [(flow.trigger_line, flow.trigger, flow.label) for flow in uc.flows]
    for line_no, text, where in cited:
        local, external = split_external(text)
        uc.external += [(line_no, context, identifier, rule_id, where) for context, identifier, rule_id in external]
        for cite in RE_RULE_CITE.finditer(local):
            uc.citations.append((line_no, cite.group(1), cite.group(2), where))
    value, line_no = uc.fields.get("Requirements", ("", 0))
    uc.external += [(line_no, context, identifier, rule_id, "Requirements") for context, identifier, rule_id in split_external(value)[1]]
    return uc


def load_use_cases(docs):
    return [parse_use_case(path) for path in docs.use_case_files()]


# --- journey test case ------------------------------------------------------

class TestCase:
    def __init__(self, path):
        self.path = path
        self.title = None
        self.fields = {}
        self.section_lines = {}
        self.roles = []
        self.preconditions = []
        self.flow_header = []
        self.flow_rows = []          # (line, row dict)
        self.validations = []        # (line, text)
        self.postconditions = []

    def field(self, label):
        return self.fields.get(label, ("", 0))[0]

    @property
    def id(self):
        match = RE_TC_ID.search(self.field("ID"))
        return match.group(0) if match else None

    def use_case_ids(self):
        ids = []
        for _, row in self.flow_rows:
            match = RE_UC_ID.search(row.get("Use Case", ""))   # link text and link target both carry the id
            if match:
                ids.append(match.group(0))
        return ids


def parse_test_case(path):
    lines = read_lines(path)
    tc = TestCase(path)
    section = None
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if line.startswith("# ") and tc.title is None:
            tc.title = re.sub(r"^Test Case:\s*", "", line[2:].strip())
            continue
        if line.startswith("## "):
            section = line[3:].strip()
            tc.section_lines[section] = number
            continue
        if not stripped:
            continue
        field, bullet, numbered = RE_FIELD.match(stripped), RE_BULLET.match(line), RE_NUMBERED.match(line)
        cells = table_cells(line)
        if section == "Overview" and field:
            tc.fields[field.group(1)] = (field.group(2), number)
        elif section == "Roles" and bullet:
            tc.roles.append((number, bullet.group(1)))
        elif section == "Preconditions" and bullet:
            tc.preconditions.append((number, bullet.group(1)))
        elif section == "Flow" and cells is not None:
            if not tc.flow_header:
                tc.flow_header = cells
            elif not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                tc.flow_rows.append((number, dict(zip(tc.flow_header, cells + [""] * (len(tc.flow_header) - len(cells))))))
        elif section == "Validation" and numbered:
            tc.validations.append((number, numbered.group(2)))
        elif section == "Postconditions" and bullet:
            tc.postconditions.append((number, bullet.group(1)))
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
    hits = {}
    files = sorted({path for path, _, _ in find_markers(root, uc.id, suffixes)})
    labels = ["Main"] + [f.label for f in uc.flows if not f.retired] + [r.id for r in uc.rules if not r.retired]
    patterns = {label: unit_pattern(label) for label in labels}
    for path in files:
        try:
            lines = read_lines(path)
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(lines, 1):
            for label, pattern in patterns.items():
                if pattern is not None and pattern.search(line):
                    hits.setdefault(label, []).append((path, number, line.strip()))
    return files, hits


def compact_id(identifier):
    """UC-001 -> UC001, the form identifiers take inside class and function names."""
    return identifier.replace("-", "")


def iter_source_files(root, globs=None, skip=(".git", "node_modules", ".venv", "venv", "dist", "build", "target", "__pycache__")):
    """Yield text files under root, skipping dependency and build folders. globs filters by suffix when given."""
    suffixes = tuple(globs) if globs else None
    for directory, names, files in os.walk(root):
        names[:] = [n for n in names if n not in skip and not n.startswith(".")]
        for name in sorted(files):
            if suffixes and not name.endswith(suffixes):
                continue
            yield os.path.join(directory, name)


def find_markers(root, uc_id, suffixes=None):
    """Find lines that carry a use case id, in plain (UC-001) or compact (UC001) form.

    Returns [(path, line number, text)]. Binary and unreadable files are skipped.
    """
    plain = re.compile(r"(?<![A-Za-z0-9])%s(?!\d)" % re.escape(uc_id))
    compact = re.compile(r"(?<![A-Za-z0-9])%s(?!\d)" % re.escape(compact_id(uc_id)))
    hits = []
    for path in iter_source_files(root, suffixes):
        try:
            with open(path, encoding="utf-8") as handle:
                for number, line in enumerate(handle, 1):
                    if plain.search(line) or compact.search(line):
                        hits.append((path, number, line.rstrip("\n")))
        except (UnicodeDecodeError, OSError):
            continue
    return hits


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
        done = subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)
    return done.returncode, done.stdout
