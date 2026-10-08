#!/usr/bin/env python3
"""The implementer's gate: check that a change to one use case is complete before it is reported.

One command for the steps that are easy to skip. It checks:

  scope    every changed file belongs to the use case, or to another use case
           the same change record names (the scope audit)
  markers  every rule in the change carries its marker UC-XXX BR-YYY in the code
  tests    every flow and rule in the change is named by a test of the use case
  guard    every rule in the change has a break that a test caught, in the guard-check
           log written by guard_check.py (DIR/reviews/guard-checks.md)
  decisions every owner decision in the change record names the specification
           element that carries it (Lives in), and that element exists; a
           decision kept only in the record is lost to the implementation
  sources  every flow and rule in the change rests on something: a row of the
           differences from today, or a row of the record's sources table naming
           the request, an owner decision, today's behavior or a listed
           assumption; behavior with none is an unmarked invention
  record   every flow and rule the specification changed since the change began
           is named in the change record (unrecorded_changes.py): a correction
           made on the way, outside the record, has no difference, source or pin
  (warns)  a rule marker right above a function that no other code refers to:
           the marker sits on code nothing calls
  (warns)  with the A-files (ACTIVE.md with a hot zone): the use case's Status moved
           since the base while ABILITIES.md and ACTIVE.md stayed unchanged
  pinning  every row of the change record whose today's behavior was only read
           from the code is pinned by a test that was there before the code
           changed: in the base, or in a commit that changed tests and documents
           only. A pin written together with the change proves the new code, not
           today's behavior; a pin of a row the change alters may since have been
           updated or replaced, and it must have been: a test that pins a behavior
           the change alters fails when it changes, so a cited test the change
           left exactly as it was does not pin that row.

The units in the change come from the change record's differences table when
there is one, else from the specification's changes since it was last
implemented, else from the whole use case. Then it prints the report fields;
the ones it cannot check (the test run, the guard check, the inventions) are
listed for the implementer to fill in.

A change record's table has the columns Element | Today | After the change |
Requested by | Seen in. Seen in says how today's behavior is known: `code` (read
from the code: pin it with a test before changing it), `test <name>` (pinned by
that test), or `observed` (seen on the running system).

Exit code 0 when everything it can check holds, 1 when something is missing or
could not be checked, 2 on usage errors.

Usage:
    finish_change.py UC-012 [--base REF] [--docs DIR] [--code DIR] [--tests DIR]
                     [--record FILE] [--format text|json]

--base defaults to HEAD (uncommitted work); on a feature branch pass the branch
it started from. --code and --tests default to the repository; test files are
recognized by their names and folders (test_x, x_test, x.test, x.spec, XTest,
tests/, __tests__/). --record defaults to the newest file in a change-records
folder under docs that is named after the use case or names it in its element
metadata or its differences table (one change may cover several use cases).

Requires Python 3.9+, standard library only, and git for the scope audit. Reads only.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_model as model  # noqa: E402  (local module, same folder)
import scope_audit  # noqa: E402
import uc_change_list  # noqa: E402
import unrecorded_changes  # noqa: E402

TEST_NAME = re.compile(r"(^test_|_test\.|\.test\.|\.spec\.|_spec\.|Tests?\.[A-Za-z]+$)")
TEST_FOLDERS = {"tests", "test", "__tests__", "spec", "specs", "e2e"}
UNIT = re.compile(r"\b(A\d+|BR-\d{3})\b")


def is_test_path(path):
    parts = path.replace("\\", "/").split("/")
    return bool(TEST_NAME.search(parts[-1])) or any(part in TEST_FOLDERS for part in parts[:-1])


def pinning_test(seen):
    """The test a Seen in cell names: the first quoted or backticked part, else the text before a parenthesis."""
    rest = re.sub(r"^test\s*:?\s*", "", seen, flags=re.IGNORECASE).strip()
    quoted = re.search(r"`([^`]+)`|\"([^\"]+)\"|«([^»]+)»|'([^']+)'", rest)
    if quoted:
        return next(group for group in quoted.groups() if group)
    return rest.split(" (")[0].strip()


def test_file_exists(root, reference):
    """A Seen in cell may name a test by its location (Login.test.tsx:230): accept it when that test file exists."""
    match = re.fullmatch(r"([\w./-]+?)(?::\d+)?", reference)
    if not match or not is_test_path(match.group(1)):
        return False
    tail = match.group(1).replace("\\", "/")
    return any(path.replace(os.sep, "/").endswith(tail) for path in model.iter_source_files(root))


def names_use_case(path, uc_id):
    """True when the record's element metadata or a row of its differences table names the use case."""
    record = model.parse_change_record(path)
    if uc_id in model.RE_UC_ID.findall(record.element):
        return True
    return any(mine for _, _, _, mine in (record_rows_from(model.read_lines(path), uc_id) or []) if mine is True)


def record_use_cases(path):
    """Every use case a change record names in its element metadata or differences table."""
    ids = set(model.RE_UC_ID.findall(model.parse_change_record(path).element))
    for cell, _, _, _ in record_rows_from(model.read_lines(path), "") or []:
        ids.update(model.RE_UC_ID.findall(cell))
    return ids


def present_at(repo, commit, name):
    """True when the revision holds the test: its name in a file, or a test file at that location."""
    location = re.fullmatch(r"([\w./-]+\.\w+)(?::\d+)?", name)      # a file, not a bare test name
    if location and is_test_path(location.group(1)):
        code, out = model.git(["ls-tree", "-r", "--name-only", commit], cwd=repo)
        return code == 0 and any(path.endswith(location.group(1)) for path in out.splitlines())
    code, _ = model.git(["grep", "-q", "-F", name, commit, "--"], cwd=repo)
    return code == 0


def pin_point(repo, base, name, docs_rel):
    """The commit where the pinning test stood before any code of the change: the base, or the first
    commit after it that has the test and whose changes since the base are tests and documents only.
    None when there is no such commit."""
    if present_at(repo, base, name):
        return base
    code, out = model.git(["rev-list", "--reverse", "%s..HEAD" % base], cwd=repo)
    for commit in (out.split() if code == 0 else []):
        if present_at(repo, commit, name):
            code, changed = model.git(["diff", "--name-only", base, commit, "--"], cwd=repo)
            ok = code == 0 and all(is_test_path(path) or path.startswith(docs_rel + "/") for path in changed.splitlines())
            return commit if ok else None
    return None


def pinned_before(repo, base, name, docs_rel):
    return pin_point(repo, base, name, docs_rel) is not None


# Where a test's block starts: a definition that names it, or a call that takes its name as text
# (it("..."), test("...")). The block runs to the next line indented no deeper than its first line.
TEST_START = re.compile(r"^\s*(?:(?:it|test|specify|scenario|describe)\s*\(|.*\b(?:def|function|func|fun|fn|void|sub)\s)")
BLOCK_LINES = 400       # longer than any single test; a bound so that a missed end cannot swallow a file


def test_block(text, name):
    """The text of the test the name points at, or None when the text does not have it."""
    lines = text.split("\n")
    word = re.compile(r"(?<![\w$])%s(?![\w$])" % re.escape(name))
    start = next((i for i, line in enumerate(lines) if word.search(line) and TEST_START.match(line)), None)
    if start is None:
        start = next((i for i, line in enumerate(lines) if word.search(line)), None)
    if start is None:
        return None
    indent = len(lines[start]) - len(lines[start].lstrip())
    block = [lines[start].rstrip()]
    for line in lines[start + 1:start + BLOCK_LINES]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            if line.strip()[0] in ")}]":
                block.append(line.rstrip())
            break
        block.append(line.rstrip())
    return "\n".join(block).rstrip()


def pin_text(name, read_files):
    """The pin's text in a set of files: the whole file for a location, else the test's block."""
    location = re.fullmatch(r"([\w./-]+\.\w+)(?::\d+)?", name)
    for path, text in read_files():
        if location and is_test_path(location.group(1)):
            if path.replace(os.sep, "/").endswith(location.group(1)):
                return text
            continue
        block = test_block(text, name)
        if block is not None:
            return block
    return None


def pin_untouched(repo, commit, name, test_root, docs_dir):
    """True when the pin reads now exactly as it did at the commit where it stood before the change."""
    def show(path):
        try:
            code, text = model.git(["show", "%s:%s" % (commit, path)], cwd=repo)
        except UnicodeDecodeError:            # a binary file that happens to contain the name
            return None
        return text if code == 0 else None

    def then():
        # -I skips binary files (compiled caches, images) that may contain the name.
        code, out = model.git(["grep", "-I", "-l", "-F", re.sub(r":\d+$", "", name), commit, "--"], cwd=repo)
        for entry in (out.splitlines() if code == 0 else []):
            path = entry.split(":", 1)[1] if ":" in entry else entry
            text = show(path) if is_test_path(path) else None
            if text is not None:
                yield path, text
        location = re.fullmatch(r"([\w./-]+\.\w+)(?::\d+)?", name)
        if location:
            code, listing = model.git(["ls-tree", "-r", "--name-only", commit], cwd=repo)
            for path in (listing.splitlines() if code == 0 else []):
                text = show(path) if path.endswith(location.group(1)) else None
                if text is not None:
                    yield path, text

    def now():
        for source in source_files(test_root, docs_dir, tests=True):
            try:
                yield os.path.relpath(source, repo), "\n".join(model.read_lines(source))
            except (OSError, UnicodeDecodeError):
                continue

    before, after = pin_text(name, then), pin_text(name, now)
    return before is not None and after is not None and before.rstrip() == after.rstrip()


def altered_cells(lines, uc_id):
    """Element cells of the differences table whose Today and After the change differ."""
    altered = set()
    for table in model.read_tables(lines):
        header = [h.strip().lower() for h in table["header"]]
        if "element" not in header or not any(h.startswith("today") for h in header):
            continue
        today = table["header"][next(i for i, h in enumerate(header) if h.startswith("today"))]
        after = next((table["header"][i] for i, h in enumerate(header) if h.startswith("after")), None)
        element = table["header"][header.index("element")]
        for _, row, _ in table["rows"]:
            cell = row.get(element, "").strip()
            if cell and (after is None or model.norm_text(row.get(today, "")) != model.norm_text(row.get(after, ""))):
                altered.add(cell)
        break
    return altered


ELEMENT_REF = re.compile(r"\b(UC-\d{3})(?:\s+(step\s+\d+|A\d+|BR-\d{3}|Post-[SF]-\d+|Pre-\d+))?", re.IGNORECASE)
NOWHERE = re.compile(r"^(?:out of scope|open|none|-|—)\b", re.IGNORECASE)


def guard_log(docs_dir):
    """Unit -> verdict of its newest row in the guard-check log; empty when there is no log."""
    path = os.path.join(docs_dir, "reviews", "guard-checks.md")
    latest = {}
    if os.path.isfile(path):
        for table in model.read_tables(model.read_lines(path)):
            if "Unit" not in table["header"] or "Verdict" not in table["header"]:
                continue
            for _, row, _ in table["rows"]:
                unit = row.get("Unit", "").strip()
                if unit:
                    latest[unit] = row.get("Verdict", "").strip()
    return latest


SOURCE = re.compile(r"^\s*(?:the\s+)?(?:(request)|(today)|decision\s+(\d+)|assumption\s+(\d+))\b", re.IGNORECASE)


def numbered(lines, column):
    """The # values of every table that has the given column (Decision, Assumption)."""
    numbers = set()
    for table in model.read_tables(lines):
        header = [h.strip().lower() for h in table["header"]]
        if "#" in header and any(h.startswith(column) for h in header):
            numbers |= {row.get("#", "").strip().strip("[]") for _, row, _ in table["rows"]}
    return numbers


def source_problems(lines, uc_id, units, rows):
    """Flows and rules of the change that rest on no source: unmarked inventions."""
    covered = {u for _, found, requested, mine in (rows or []) if mine is not False for u in found}
    decisions, assumptions = numbered(lines, "decision"), numbered(lines, "assumption")
    sourced, named, problems = set(), set(), []
    for table in model.read_tables(lines):
        header = [h.strip().lower() for h in table["header"]]
        if "element" not in header or "source" not in header:
            continue
        element_col, source_col = table["header"][header.index("element")], table["header"][header.index("source")]
        for _, row, _ in table["rows"]:
            cell, source = row.get(element_col, "").strip(), row.get(source_col, "").strip()
            if not cell or cell.startswith("["):
                continue
            if uc_id not in cell and model.RE_UC_ID.search(cell):
                continue
            match = SOURCE.match(source)
            for unit in UNIT.findall(cell):
                named.add(unit)
                if not match:
                    problems.append("%s %s names a source that is not the request, today, a decision or an assumption: %s" % (uc_id, unit, source or "empty"))
                elif match.group(3) and match.group(3) not in decisions:
                    problems.append("%s %s rests on decision %s, which the record's decisions table does not have" % (uc_id, unit, match.group(3)))
                elif match.group(4) and match.group(4) not in assumptions:
                    problems.append("%s %s rests on assumption %s, which the record's assumptions table does not have" % (uc_id, unit, match.group(4)))
                else:
                    sourced.add(unit)
    problems += ["%s %s rests on no source: name the request, an owner decision, today's behavior or a listed assumption in the change record" % (uc_id, u)
                 for u in units if u not in covered and u not in named]
    return problems


def decision_problems(lines, docs):
    """Owner decisions whose Lives in cell is empty or names an element no specification has."""
    problems, specs = [], {}
    for table in model.read_tables(lines):
        header = [h.strip().lower() for h in table["header"]]
        if not any(h.startswith("decision") for h in header) or "lives in" not in header:
            continue
        lives = table["header"][header.index("lives in")]
        what = table["header"][next(i for i, h in enumerate(header) if h.startswith("decision"))]
        for _, row, _ in table["rows"]:
            decision, cell = row.get(what, "").strip(), row.get(lives, "").strip().strip("`")
            if not decision or decision.startswith("["):
                continue
            label = decision if len(decision) <= 60 else decision[:57] + "..."
            if NOWHERE.match(cell):
                continue
            refs = ELEMENT_REF.findall(cell)
            if not refs:
                problems.append("owner decision '%s' names no element that carries it (Lives in: a use case element, out of scope, or open)" % label)
                continue
            for uc_id, part in refs:
                if uc_id not in specs:
                    path = uc_change_list.find_spec(docs, uc_id)
                    specs[uc_id] = model.parse_use_case(path) if path else None
                spec = specs[uc_id]
                if spec is None:
                    problems.append("owner decision '%s' lives in %s, which has no specification" % (label, uc_id))
                elif part and not element_exists(spec, part):
                    problems.append("owner decision '%s' lives in %s %s, which that specification does not have" % (label, uc_id, part))
    return problems


def element_exists(spec, part):
    part = part.strip()
    low = part.lower()
    if low.startswith("step"):
        return int(low.split()[-1]) in [s.number for s in spec.steps]
    if part.upper().startswith("BR-"):
        return part.upper() in [r.id for r in spec.rules]
    if low.startswith("post-"):
        kind, number = part.split("-")[1].upper(), int(part.split("-")[2])
        return number <= len(spec.success if kind == "S" else spec.failure)
    if low.startswith("pre-"):
        return int(part.split("-")[1]) <= len(spec.preconditions)
    return part.upper() in [f.label for f in spec.flows]


def find_record(docs, uc_id):
    """The newest change record named after the use case or naming it; None when there is none."""
    found = []
    for path in docs.change_record_files():
        name = os.path.basename(path)
        if name == uc_id + ".md" or name.startswith(uc_id + "-") or names_use_case(path, uc_id):
            found.append(path)
    return max(found, key=lambda path: (os.path.getmtime(path), path)) if found else None


def record_rows(path, uc_id):
    """Rows of the differences table: [(element cell, units, seen in or None, mine)]; None when no such table.

    mine is True when the row names this use case, None when it names none (it belongs to the
    change as a whole), False when it names only another use case.
    """
    return record_rows_from(model.read_lines(path), uc_id)


def record_rows_from(lines, uc_id):
    for table in model.read_tables(lines):
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
            other = [u for u in model.RE_UC_ID.findall(cell) if u != uc_id]
            mine = True if uc_id in cell else (False if other else None)
            units = [] if mine is False else UNIT.findall(cell)
            rows.append((cell, units, row.get(seen_col, "").strip() if seen_col else None, mine))
        return rows
    return None


def units_in_change(uc, repo, rel, record):
    """(units, where they came from)."""
    if record:
        rows = record_rows(record, uc.id)
        if rows is not None:
            units = sorted({u for _, found, _, _ in rows for u in found})
            return units, "the change record %s" % os.path.relpath(record)
    if repo:
        base = uc_change_list.find_base(repo, rel)
        old = uc_change_list.revision_text(repo, base, rel) if base else None
        if old is not None:
            changes = uc_change_list.compare(model.parse_use_case_lines(old.split("\n"), rel), uc)
            units = sorted({c["element"] for c in changes if c["change"] in ("added", "changed") and UNIT.fullmatch(c["element"])})
            return units, "the specification's changes since %s" % base[:12]
    units = [f.label for f in uc.flows if not f.retired] + [r.id for r in uc.rules if not r.retired]
    return units, "the whole use case (no change record, no implemented revision)"


def source_files(root, docs_dir, tests):
    docs_abs = os.path.abspath(docs_dir)
    for path in model.iter_source_files(root):
        full = os.path.abspath(path)
        if full.startswith(docs_abs + os.sep):
            continue
        if is_test_path(os.path.relpath(full, root)) == tests:
            yield path


def tracking_warning(repo, base, rel, uc):
    """P6 of the pairing: a Status move without ABILITIES.md or ACTIVE.md in step, as text; None when it does not apply."""
    if not repo or not rel or not model.a_files_present(repo):
        return None
    code, before = model.git(["show", "%s:%s" % (base, rel)], cwd=repo)
    if code != 0:
        return None          # the specification is new since the base: its first Status is no move
    previous = model.parse_use_case_lines(before.split("\n"), rel).status
    if not previous or previous == uc.status:
        return None
    code, out = model.git(["diff", "--name-only", base, "--", "ABILITIES.md", "ACTIVE.md"], cwd=repo)
    if code == 0 and out.strip():
        return None
    return ("%s moved from %s to %s and neither ABILITIES.md nor ACTIVE.md changed: update the ability whose Specs line "
            "names it, and the current work, in the same commit" % (uc.id, previous, uc.status))


def check(args):
    problems, result = [], {}
    docs = model.Docs(args.docs)
    path = uc_change_list.find_spec(docs, args.use_case)
    if not path:
        raise SystemExit("no specification file for %s under %s" % (args.use_case, args.docs))
    uc = model.parse_use_case(path)
    code, top = model.git(["rev-parse", "--show-toplevel"], cwd=os.path.dirname(os.path.abspath(path)))
    repo = top.strip() if code == 0 else None
    rel = os.path.relpath(os.path.realpath(path), os.path.realpath(repo)).replace(os.sep, "/") if repo else None
    record = args.record or find_record(docs, uc.id)
    formats = []
    if record:
        record_docs = model.Docs(args.docs)
        record_docs.change_record_files = lambda: [record]
        formats = model.format_findings(record_docs, kinds=("record",))
        problems += ["record format %s: %s" % (code, message) for _, _, code, message in formats]
    result["formats"] = formats
    units, origin = units_in_change(uc, repo, rel, record)
    result.update({"use_case": uc.id, "units": units, "units_from": origin, "record": os.path.relpath(record) if record else None})

    docs_rel = os.path.relpath(os.path.realpath(args.docs), os.path.realpath(repo)).replace(os.sep, "/") if repo else None

    # guard checks
    log = guard_log(args.docs)
    guard = {"checked": [u for u in units if u.startswith("BR-")], "caught": [], "missing": []}
    for rule in guard["checked"]:
        verdict = log.get("%s %s" % (uc.id, rule), "")
        (guard["caught"] if verdict == "caught" else guard["missing"]).append(rule if not verdict else "%s (%s)" % (rule, verdict))
    result["guard"] = guard
    problems += ["no logged break of %s %s that a test caught: run scripts/guard_check.py" % (uc.id, m) for m in guard["missing"]]

    # sources of the flows and rules in the change
    record_lines = model.read_lines(record) if record else []
    sources = source_problems(record_lines, uc.id, units, record_rows(record, uc.id)) if record else []
    result["sources"] = sources
    problems += sources

    # owner decisions
    decisions = decision_problems(record_lines, docs) if record else []
    result["decisions"] = decisions
    problems += decisions

    # specification changes the record does not name
    if not record:
        result["specification"] = "not checked: no change record"
    else:
        try:
            spec = unrecorded_changes.check(args.docs, uc.id, record)
        except unrecorded_changes.Undecidable as exc:
            result["specification"] = "not checked: %s" % exc
        else:
            result["specification"] = {"since": spec["since"], "unrecorded": spec["unrecorded"]}
            problems += ["%s %s was %s in the specification since the change began (%s), but the change record does not name it: "
                         "record it (a difference from today with its source, or a correction with why) or undo it"
                         % (uc.id, c["unit"], c["change"], spec["since"][:12]) for c in spec["unrecorded"]]

    # scope
    if not repo:
        result["scope"] = "not run: git is not available here"
        problems.append("the scope audit could not run (no git); compare the changed files with the plan by hand and say so")
    else:
        files = scope_audit.changed_files(repo, args.base)
        if files is None:
            raise SystemExit("unknown revision: %s; pass the branch or commit the change started from, or HEAD while nothing is committed" % args.base)
        ids = sorted({uc.id} | (record_use_cases(record) if record else set()))
        alternatives = "|".join(re.escape(i) for i in ids)
        compacts = "|".join(re.escape(model.compact_id(i)) for i in ids)
        plain = re.compile(r"(?<![A-Za-z0-9])(?:%s)(?!\d)" % alternatives)
        compact = re.compile(r"(?<![A-Za-z0-9])(?:%s)(?!\d)" % compacts)
        unattributed = [p for p, status in sorted(files.items())
                        if not p.startswith(docs_rel + "/") and not plain.search(p) and not compact.search(p)
                        and not (status != "D" and scope_audit.carries(os.path.join(repo, p), (plain, compact)))]
        result["scope"] = {"changed": len(files), "unattributed": unattributed, "use_cases": ids}
        problems += ["%s changed but carries no %s: explain it, split it out or revert it" % (p, " or ".join(ids)) for p in unattributed]

    # markers
    code_root = args.code or repo or "."
    rules = [u for u in units if u.startswith("BR-")]
    marker = {rule: re.compile(r"(?<![A-Za-z0-9])%s\s+%s(?!\d)" % (re.escape(uc.id), rule)) for rule in rules}
    found, texts, defined = set(), [], []
    for source in source_files(code_root, args.docs, tests=False):
        try:
            lines = model.read_lines(source)
        except (OSError, UnicodeDecodeError):
            continue
        texts.append("\n".join(lines))
        for index, line in enumerate(lines):
            for rule, pattern in marker.items():
                if pattern.search(line):
                    found.add(rule)
                    name = model.marked_definition(lines, index)
                    if name:
                        defined.append((rule, os.path.relpath(source), index + 1, name))
    missing_markers = [r for r in rules if r not in found]
    # A warning, not a problem: the definition may be called by a framework that never names it.
    uncalled = ["%s at %s:%d marks %s(), which no other code refers to" % (rule, path, line, name)
                for rule, path, line, name in defined if model.count_references(name, texts) <= 1]
    result["markers"] = {"checked": rules, "missing": missing_markers, "uncalled": uncalled}
    problems += ["no code carries the marker %s %s" % (uc.id, r) for r in missing_markers]

    # tests
    test_root = args.tests or repo or "."
    files, hits = model.scan_units(test_root, uc)
    named = {label for label, places in hits.items()
             if any(is_test_path(os.path.relpath(p, test_root)) and not os.path.abspath(p).startswith(os.path.abspath(args.docs) + os.sep) for p, _, _ in places)}
    untested = [u for u in units if u not in named]
    result["tests"] = {"checked": units, "missing": untested}
    problems += ["no test of %s names %s" % (uc.id, u) for u in untested]

    # pinning
    rows = record_rows(record, uc.id) if record else None
    pin = {"rows": 0, "unpinned": [], "untouched": []}
    altered = altered_cells(record_lines, uc.id) if record else set()
    if rows is not None:
        test_text = []
        for source in source_files(test_root, args.docs, tests=True):
            try:
                test_text.append("\n".join(model.read_lines(source)))
            except (OSError, UnicodeDecodeError):
                continue
        test_text = "\n".join(test_text)
        for cell, _, seen, mine in rows:
            if mine is False:
                continue                       # a row of another use case in the same change
            pin["rows"] += 1
            if seen is None:
                pin["unpinned"].append("%s: the record has no Seen in column" % cell)
                continue
            how = seen.lower()
            if how.startswith("observed"):
                continue
            name = pinning_test(seen)
            if not (how.startswith("test") and name):
                pin["unpinned"].append("%s: read from the code, not pinned by a test" % cell)
                continue
            point = pin_point(repo, args.base, name, docs_rel) if repo else None
            if point:
                # Pinned before the change. A row the change alters needs that pin updated or replaced.
                if cell in altered and pin_untouched(repo, point, name, test_root, args.docs):
                    pin["untouched"].append("%s: the change alters this row but leaves %s exactly as it was, so that test does not "
                                            "pin what changes; pin the row with a test that asserts its Today cell, then update "
                                            "or replace that test with the change" % (cell, name))
                continue
            if name in test_text or test_file_exists(test_root, name):
                if repo:
                    pin["unpinned"].append("%s: the test %s was written with the change, not before it; pin against today's code, "
                                           "commit the pin, then change the code" % (cell, name))
                continue
            pin["unpinned"].append("%s: the test %s does not exist" % (cell, name))
    result["pinning"] = pin
    problems += ["pin today's behavior before changing it: %s" % item for item in pin["unpinned"]]
    problems += ["a pin the change did not touch: %s" % item for item in pin["untouched"]]
    result["tracking"] = tracking_warning(repo, args.base, rel, uc)
    result["problems"] = problems
    return result


def print_text(r, base):
    for path, line, code, message in r.get("formats", []):
        print("%s:%d: ERROR %s [-]: %s" % (path, line, code, message))
    print("%s  finish check against %s" % (r["use_case"], base))
    print("Units in the change (from %s): %s" % (r["units_from"], ", ".join(r["units"]) or "none"))
    scope = r["scope"]
    if isinstance(scope, str):
        print("Scope audit:  %s" % scope)
    else:
        print("Scope audit:  %s" % ("ok: %d changed file(s), all attributed" % scope["changed"] if not scope["unattributed"]
                                    else "%d unattributed: %s" % (len(scope["unattributed"]), ", ".join(scope["unattributed"]))))
    m = r["markers"]
    print("Markers:      %s" % ("ok: %s" % (", ".join(m["checked"]) or "no rule in the change") if not m["missing"] else "missing: %s" % ", ".join(m["missing"])))
    for warning in m.get("uncalled", []):
        print("  warning:    %s; the rule is enforced where it is called" % warning)
    print("Sources:      %s" % ("ok" if not r.get("sources") else "%d flows or rules rest on no source" % len(r["sources"])))
    d = r.get("decisions", [])
    print("Decisions:    %s" % ("ok" if not d else "%d without a home in the specifications" % len(d)))
    s = r.get("specification", "not checked")
    print("Record:       %s" % (s if isinstance(s, str) else "ok: every changed flow and rule is named" if not s["unrecorded"]
                                else "changed outside the record: %s" % ", ".join(c["unit"] for c in s["unrecorded"])))
    t = r["tests"]
    print("Tests named:  %s" % ("ok: %s" % (", ".join(t["checked"]) or "nothing to name") if not t["missing"] else "no test names %s" % ", ".join(t["missing"])))
    p = r["pinning"]
    if r["record"] is None:
        print("Pinning:      no change record")
    else:
        issues = p["unpinned"] + p.get("untouched", [])
        print("Pinning:      %s" % ("ok: %d row(s)" % p["rows"] if not issues else "%d of %d row(s) not pinned (see below)" % (len(issues), p["rows"])))
    g = r.get("guard", {"checked": [], "missing": [], "caught": []})
    print("Guard check:  %s" % ("logged and caught: %s" % ", ".join(g["caught"]) if g["checked"] and not g["missing"]
                                  else "missing for %s (run scripts/guard_check.py)" % ", ".join(g["missing"]) if g["missing"]
                                  else "no rule in the change"))
    if r.get("tracking"):
        print("Tracking:     warning: %s" % r["tracking"])
    print("To fill in by hand:")
    print("  Tests run:    <the suite's result before and after the change>")
    print("  Inventions:   <asked / assumed / declared free>")
    if r["problems"]:
        print("Result: not ready, %d problem(s)" % len(r["problems"]))
        for problem in r["problems"]:
            print("  - %s" % problem)
    else:
        print("Result: ready to report")


def main(argv):
    parser = argparse.ArgumentParser(description="Check that a change to one use case is complete.")
    parser.add_argument("use_case", help="identifier, for example UC-012")
    parser.add_argument("--base", default="HEAD")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--code", help="folder with the implementation (default: the repository)")
    parser.add_argument("--tests", help="folder with the tests (default: the repository)")
    parser.add_argument("--record", help="change record with the differences from today")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    args.docs = args.docs or model.docs_default()
    if not re.fullmatch(r"UC-\d{3}", args.use_case):
        print("use case identifier must look like UC-012", file=sys.stderr)
        return 2
    for folder in (args.docs, args.code, args.tests):
        if folder and not os.path.isdir(folder):
            print("no such folder: %s" % folder, file=sys.stderr)
            return 2
    if args.record and not os.path.isfile(args.record):
        print("no such file: %s" % args.record, file=sys.stderr)
        return 2
    docs = model.Docs(args.docs)
    if args.record:
        records = docs.change_record_files()
        docs.change_record_files = lambda: sorted(set(records + [args.record]))
    stop = model.stop_if_old(docs)
    if stop is not None:
        return stop
    try:
        result = check(args)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, UnicodeDecodeError) as exc:
        print("%s:0: ERROR UNREADABLE: cannot read: %s" % (args.record or args.docs, exc), file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_text(result, args.base)
    return 1 if result["problems"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
