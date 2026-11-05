#!/usr/bin/env python3
"""One entry point for the agent hooks, whatever tool calls it.

    hook_gate.py session-start [--docs DIR]
        the state of the specifications, as context for a new session
    hook_gate.py after-edit [PATH ...] [--docs DIR]
        the validator on every use case specification among the edited files
    hook_gate.py before-stop [--docs DIR] [--base REF]
        one question per drift for the person, each asked once in a session
    hook_gate.py turn-start [--docs DIR]
        changed open-work context, always non-blocking
    hook_gate.py later TEXT
        record a drift the person chose to align later: an item in AHEAD.md
        when the project uses the A-files, else a line in up-deferred.txt in
        the git folder, listed with the open work at session start

Every moment accepts --emit raw|claude|codex|antigravity|kiro (default: raw).
A profile renders the internal result for the calling tool.

Edited paths come from the arguments and from the JSON the tool writes to
stdin: every string under a key that names a file path, and the file names on
the "*** Update File:", "*** Add File:" and "*** Move to:" lines of a patch body. Paths that
belong to the session (transcript, working directory, workspace) are ignored,
and a relative path is read from the session's directory when the JSON names
one. A change record is never taken for a specification, even when its name
starts with a use case's identifier.

The tools inform; they never stop the work. Open records and specification
findings are work in progress shown as context. At the end of a turn the gate
looks for drift: a Status raised in this session without its evidence (against
the session's snapshot, or HEAD without one), an open change record, behavior
code changed without a specification, a broken A-files shape. Each drift not
asked yet in this session becomes one question for the person: align it now,
at the end of the session, or later. The snapshot remembers what was asked, so
the same drift is never raised again in that session. Turn start reuses
validation and prints a changed open-work list within a short wall-clock cap.

The result is the same for every tool; the tool's hook configuration maps it:

    0  pass; text on stdout, if any, is context to add
    1  warn; information, never blocking: shown where the tool has a channel
       (after an edit, the findings reach the agent as context where it can)
    2  ask; only at the end of a turn: the questions for the person, which the
       tool delivers by continuing the agent's turn once
    3  the gate could not run (no git repository, a script missing, bad
       usage); never block on it

Every firing appends one line to up-hooks.log in the repository's git
folder: the evidence that a hook fires.

The scripts it imports must sit in its own folder: change_view.py, hook_profiles.py,
workflow_state.py, validate_use_case.py, and finish_change.py with scope_audit.py,
uc_change_list.py, unrecorded_changes.py, use_case_map.py and spec_model.py.
scaffold_docs.py --hooks copies them together into tools/specs/.

Requires Python 3.9+, standard library only, and git.
"""
import argparse
from contextlib import redirect_stdout, redirect_stderr
from typing import NamedTuple, Optional
import datetime
import hashlib
import io
import json
import math
import os
import re
import shlex
import subprocess
import sys
import threading
import tempfile
import time

# the release these copies belong to; hook_gate.py refuses siblings of another release
UPSPEC_VERSION = "1.5.0"

sys.dont_write_bytecode = True   # a __pycache__ folder in tools/specs/ would be an unexplained file in every change

HERE = os.path.dirname(os.path.abspath(__file__))
UC_ID = re.compile(r"\bUC-\d{3}\b")
STDIN_WAIT = 1.0                # seconds: hook runners write their JSON at once; a terminal never writes
MAX_CONTEXT_LINES = 60          # a longer state report is cut; the full one is one command away
LOG_LINES = 200                 # a proof session and some days of work; older lines are dropped
LOG_NAME = "up-hooks.log"
# Drifts the person chose to align later, when the project keeps no AHEAD.md the gate can add to.
DEFERRED_NAME = "up-deferred.txt"
PASS, WARN, ASK, FAILED = 0, 1, 2, 3
MODES = ("session-start", "after-edit", "before-stop", "turn-start")
# Each session owns one git-folder JSON file.
SESSION_PREFIX = "up-session-"
# Where a session remembers the questions it asked when the git folder cannot be written.
ASKED_FALLBACK_PREFIX = "up-asked-"
# Sixteen hexadecimal digits (64 bits) of the root and session keep the file name short; two sessions sharing one
# temporary folder do not collide in practice. The session snapshots use the same length.
FALLBACK_KEY_DIGITS = 16
# Five lines of the A-files check show what is broken; the check itself has the rest.
A_FILES_LINES = 5
# The A-files check reads five small files and asks git for the last commit: a second in practice. Thirty
# seconds leaves room on a slow disk and keeps the end of a turn from waiting on a check that hangs.
A_FILES_TIMEOUT_SECONDS = 30
# How the A-files check prints a problem, as its documentation states: path:line: ERROR CODE: message.
A_FILES_FINDING = re.compile(r"^(?P<path>[^\s:][^:]*):(?P<line>\d+): ERROR (?P<code>[A-Z_]+): (?P<message>.*)$")
# What a finding's message names, its subject: an identifier (AB-001), a quoted or bold name, or a path (with a slash
# or a file extension, as the A-files check tells a path). Counts, positions and the wording around them are not
# part of it, so a hot zone one line longer, or a byte that moved, is the same finding.
A_FILES_SUBJECT = re.compile(r"\b[A-Z]+-\d+\b|\*\*[^*]+\*\*|'[^']*'|\"[^\"]*\"|[^\s'\":,;()]*/[^\s'\":,;()]*"
                             r"|[^\s'\":,;()/]+\.[A-Za-z0-9]{1,5}\b")
# Parallel sessions in a worktree are rare; eight leaves room without indefinite growth.
SESSION_SLOTS = 8
# A minute protects bursts of concurrent hook updates before inactive sessions are trimmed.
SNAPSHOT_PRUNE_GRACE_SECONDS = 60
# A day exceeds normal hook lifetimes by far, leaving active temporary writes alone.
SNAPSHOT_TEMP_MAX_AGE_SECONDS = 24 * 60 * 60
# Fifteen items fit a glance; a final line counts omitted items.
OPEN_LINES = 15
# Three seconds bounds per-prompt work while allowing local git and cached validation.
TURN_START_SECONDS = 3
# Four seconds cover interpreter startup, imports, root lookup and other local git bookkeeping.
TURN_START_MARGIN_SECONDS = 4
# The tool must allow stdin, computation and startup overhead before killing the hook.
TURN_START_TIMEOUT = math.ceil(TURN_START_SECONDS + STDIN_WAIT + TURN_START_MARGIN_SECONDS)
# Keep the instruction shared between session and turn context.
OPEN_HEADING = ("Work in progress, for information: fix an item only when it belongs to the current task. "
                "A use case is marked Implemented or Tested once its items are clean; the push check reports the rest.")
# The question at the end of a turn: what the person is asked and what each answer means.
QUESTION_HEADING = ("The work has drifted from the specifications or the A-files. Before you end your turn, ask the "
                    "person one question for each item below: align it now, at the end of the session, or later? "
                    "Then do what the answer means:")
QUESTION_CLOSING = ("Each item is asked once in this session and will not be raised again. "
                    "Change nothing the person did not ask for.")
# Match the installed hook bundle without importing possibly incompatible siblings.
BUNDLE_SCRIPTS = ("status_claims.py", "workflow_state.py", "validate_use_case.py", "finish_change.py", "scope_audit.py",
                  "uc_change_list.py", "unrecorded_changes.py", "spec_model.py", "use_case_map.py",
                  "change_view.py", "hook_profiles.py")
# Match the literal release constants exactly as the package version test does.
VERSION_LINE = re.compile(r'^UPSPEC_VERSION = "(\d+\.\d+\.\d+)"$', re.M)


class Verdict(NamedTuple):
    result: int
    text: str
    detail: str


class Drift(NamedTuple):
    """One way the work drifted.

    keys: its identity in the session, one per subject (a claim, a record, the change code moved in, an A-files
    finding);
    the drift is asked when one of its keys was not asked yet. title and detail: what to show. align: how to align
    it now. later_text: the text 'later' records."""
    keys: tuple
    title: str
    detail: list
    align: str
    later_text: str


class AheadPlan(NamedTuple):
    """Where an item goes in AHEAD.md: the line of the new index row, the index header's cells, the line before
    which the entry goes."""
    row: int
    header: list
    entry: int


class DeferredItem(NamedTuple):
    """A line of the deferred list: the date it was recorded and the drift's text."""
    date: str
    text: str


class GateError(Exception):
    """The gate cannot run; it answers 3 and never blocks."""


def git(cwd, *args):
    """Run git; returns (exit code, stdout as written)."""
    done = subprocess.run(["git", "-c", "core.quotePath=false"] + list(args), cwd=cwd,
                          capture_output=True, text=True)
    return done.returncode, done.stdout


def repo_root(start):
    code, out = git(start, "rev-parse", "--show-toplevel")
    if code:
        raise GateError("not inside a git repository: %s" % start)
    return out.strip()


def git_path(root, name):
    """A file in the repository's own git folder; a worktree has its own."""
    code, out = git(root, "rev-parse", "--git-path", name)
    if code:
        return None
    out = out.strip()
    return out if os.path.isabs(out) else os.path.join(root, out)


def bundle_problem(here: str) -> Optional[str]:
    """Reject missing, unversioned or mixed siblings before running any check."""
    problems = []
    for name in BUNDLE_SCRIPTS:
        try:
            with open(os.path.join(here, name), encoding="utf-8") as handle:
                found = VERSION_LINE.search(handle.read())
        except FileNotFoundError:
            problems.append("%s is missing" % name)
            continue
        except (OSError, UnicodeError) as exc:
            problems.append("%s cannot be read: %s" % (name, exc))
            continue
        if found is None:
            problems.append("%s has no UPSPEC_VERSION (gate %s)" % (name, UPSPEC_VERSION))
        elif found.group(1) != UPSPEC_VERSION:
            problems.append("%s is version %s (gate %s)" % (name, found.group(1), UPSPEC_VERSION))
    if problems:
        return "; ".join(problems) + "; refresh the bundle with scaffold_docs.py --update"
    return None


def docs_folder(root):
    """The specification folder the rules block records, else docs; docs when the parser is not beside the gate."""
    try:
        import spec_model
    except ImportError:
        return "docs"
    return spec_model.docs_default(root)


def read_stdin():
    """The JSON a hook runner wrote, or None. Never waits long on a stream nobody writes to."""
    try:
        if sys.stdin is None or sys.stdin.isatty():
            return None
        fd = sys.stdin.fileno()
    except (AttributeError, OSError, ValueError):
        return None
    box = []

    def drain():
        chunks = []
        try:
            while True:
                chunk = os.read(fd, 65536)
                if not chunk:
                    break
                chunks.append(chunk)
                try:
                    box.append(json.loads(b"".join(chunks).decode("utf-8")))
                    return
                except (ValueError, UnicodeDecodeError):
                    continue
        except OSError:
            pass

    # os.read holds no lock of Python's own, so a reader still blocked does not stall the exit
    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    reader.join(STDIN_WAIT)
    return box[0] if box else None


def specifications(root, base, docs, paths):
    """The use case specifications among the paths, relative to the root."""
    real_root = os.path.realpath(root)
    sys.path.insert(0, HERE)
    import spec_model
    docs_model = spec_model.Docs(os.path.join(root, docs))
    found = set()
    for path in paths:
        full = os.path.realpath(path if os.path.isabs(path) else os.path.join(base, path))
        try:
            rel = os.path.relpath(full, real_root).replace(os.sep, "/")
        except ValueError:          # another drive
            continue
        if docs_model.kind(full) == "use_case" and os.path.isfile(full):
            found.add(rel)
    return sorted(found)


def could_not_run(name, exc):
    return Verdict(FAILED, "%s could not run: %s: %s" % (name, type(exc).__name__, exc), "")


def _snapshot_path(root, session):
    # Sixteen hex characters bound the filename while keeping session ids out of git-folder paths.
    key = hashlib.sha256(session.encode("utf-8")).hexdigest()[:16] if session is not None else "none"
    return git_path(root, SESSION_PREFIX + key + ".json")


def _remove_old_session_file(path, selected, minimum_age):
    """Move a candidate aside, then delete the selected file or restore a refreshed one."""
    if time.time() - selected.st_mtime <= minimum_age:
        return
    fd, renamed = tempfile.mkstemp(prefix=os.path.basename(path) + ".pruning-", suffix=".tmp",
                                   dir=os.path.dirname(path))
    os.close(fd)
    discard = True
    try:
        try:
            os.rename(path, renamed)
        except FileNotFoundError:
            return  # Another pruner has already moved this candidate.
        # Keep the moved file recoverable if checking or restoring fails unexpectedly.
        discard = False
        current = os.stat(renamed, follow_symlinks=False)
        if ((current.st_dev, current.st_ino, current.st_mtime_ns)
                != (selected.st_dev, selected.st_ino, selected.st_mtime_ns)
                or time.time() - current.st_mtime <= minimum_age):
            try:
                os.link(renamed, path)
            except FileExistsError:
                pass  # A still newer file at the session's own name wins.
        discard = True
    finally:
        if discard:
            forget(renamed)


def _prune_snapshots(folder):
    """Trim inactive sessions toward the cap and clean abandoned temporary writes."""
    files, temporary = [], []
    name = re.escape(SESSION_PREFIX) + r"(?:[0-9a-f]{16}|none)\.json"
    with os.scandir(folder) as entries:
        for entry in entries:
            snapshot = re.fullmatch(name, entry.name)
            partial = re.fullmatch(name + r"\..+\.tmp", entry.name)
            if not snapshot and not partial:
                continue
            try:
                if entry.is_file(follow_symlinks=False):
                    (files if snapshot else temporary).append((entry.path, entry.stat(follow_symlinks=False)))
            except FileNotFoundError:
                continue
    files.sort(key=lambda item: (item[1].st_mtime_ns, item[0]), reverse=True)
    for path, selected in files[SESSION_SLOTS:]:
        _remove_old_session_file(path, selected, SNAPSHOT_PRUNE_GRACE_SECONDS)
    for path, selected in temporary:
        _remove_old_session_file(path, selected, SNAPSHOT_TEMP_MAX_AGE_SECONDS)


def _snapshot_save(root, session, update=None, docs_rel=None, baseline=None):
    """Atomically replace only this session's slot, then prune older session files.

    A new slot records the Statuses on disk, or at the baseline ref when one is given."""
    import status_claims
    path = _snapshot_path(root, session)
    slot = snapshot_read(root, session)
    if slot is None:
        if docs_rel is None:
            return
        code, head = git(root, "rev-parse", "--verify", "HEAD")
        slot = {"session": session, "time": datetime.datetime.now().isoformat(),
                "head": head.strip() if code == 0 else None,
                "statuses": status_claims.statuses(root, docs_rel, baseline), "shown": None, "validated": {},
                "asked": []}
    if update:
        # Cache updates must preserve the session's original baseline.
        slot.update({key: update[key] for key in ("shown", "validated") if key in update})
        if "asked" in update:
            # A slower writer's copy never forgets a question asked since it read the slot.
            slot["asked"] = sorted(set(slot.get("asked", [])) | set(update["asked"]))
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=os.path.dirname(path),
                                         prefix=os.path.basename(path) + ".", suffix=".tmp", delete=False) as handle:
            temporary = handle.name
            json.dump(slot, handle)
        os.replace(temporary, path)
    finally:
        forget(temporary)
    _prune_snapshots(os.path.dirname(path))


def snapshot_write(root, docs_rel, session) -> None:
    """Keep a resumed session's baseline; inability to save never changes hook behavior."""
    try:
        _snapshot_save(root, session, docs_rel=docs_rel)
    except BaseException as exc:
        try:
            log(root, "session-start", PASS, "snapshot write failed: %s" % exc)
        except BaseException:
            pass  # Snapshot storage and even logging failure must never escape this API.


def snapshot_read(root, session) -> Optional[dict]:
    """Read this session alone; missing or malformed state has no baseline."""
    try:
        with open(_snapshot_path(root, session), encoding="utf-8") as handle:
            slot = json.load(handle)
        if (isinstance(slot, dict)
                and {"session", "time", "head", "statuses", "shown", "validated"} <= set(slot)
                and slot["session"] == session
                and (slot["session"] is None or isinstance(slot["session"], str))
                and isinstance(slot["time"], str)
                and (slot["head"] is None or isinstance(slot["head"], str))
                and isinstance(slot["statuses"], dict)
                and all(isinstance(key, str) and isinstance(value, list) and len(value) == 2
                        and all(isinstance(item, str) for item in value)
                        for key, value in slot["statuses"].items())
                and (slot["shown"] is None or isinstance(slot["shown"], str))
                and isinstance(slot["validated"], dict)
                and (isinstance(slot.get("asked", []), list)
                     and all(isinstance(key, str) for key in slot.get("asked", [])))):
            slot.setdefault("asked", [])       # a slot saved before questions were remembered
            return slot
    except (OSError, ValueError, TypeError, UnicodeError):
        pass
    return None


def _list_digest(lines):
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def _titles(root, docs_rel) -> dict:
    """The identifiers' titles; none when a file cannot be read, since a title is never worth a failed hook."""
    import spec_model as model
    try:
        folder = os.path.join(root, docs_rel)
        return model.known_titles(root, model.Docs(folder) if os.path.isdir(folder) else None)
    except (OSError, UnicodeError, ValueError, AttributeError, KeyError, TypeError) as exc:
        log(root, "titles", PASS, "titles not read: %s" % exc)
        return {}


def open_list(view, docs_rel, slot) -> list[str]:
    """Read git paths and docs only; reuse validation while its inputs stay unchanged."""
    import spec_model as model
    import status_claims
    import validate_use_case
    lines = ["- Open change record: " + name for name in open_records(view)]
    deferred = deferred_items(view.root)
    lines += ["- Deferred: %s (since %s)" % (item.text, item.date) for item in deferred]
    if deferred:
        lines.append("- Deferred items are lines of %s in the git folder; remove a line once it is aligned."
                     % DEFERRED_NAME)
    current = status_claims.statuses(view.root, docs_rel)
    before = status_claims.statuses(view.root, docs_rel, view.base.commit) if view.base.commit else {}
    raised = {claim.uc: claim for claim in status_claims.find_claims(before, current)}
    # An unreadable edited spec has no parsed Status, but its error still belongs here.
    current_paths = {value[0] for value in current.values()}
    previous_paths = {path: (uc, status) for uc, (path, status) in before.items()}
    for path in view.changed_specs():
        if path not in current_paths:
            uc, status = previous_paths.get(path, (path, ""))
            current[uc if uc not in current else path] = (path, status)
    # Publish immutable copies after each completed validation, so a capped caller
    # can save a coherent partial cache while the daemon finishes its current file.
    cache = dict(slot.setdefault("validated", {}))
    # Validation uses the catalog, entities and other specs for recognition, so their bytes
    # participate in the key too. A cross-file correction must invalidate a cached error.
    docs_digest = hashlib.sha256()
    for directory, folders, names in os.walk(view.docs.root):
        folders.sort()
        for name in sorted(names):
            path = os.path.join(directory, name)
            # Legacy diagram presence also affects format recognition.
            if not name.endswith((".md", ".puml")):
                continue
            docs_digest.update(path.encode("utf-8"))
            try:
                with open(path, "rb") as handle:
                    docs_digest.update(handle.read())
            except OSError as exc:
                docs_digest.update(str(exc).encode("utf-8"))
    context_digest = docs_digest.hexdigest()
    for uc, (path, status) in sorted(current.items()):
        strict = model.STATUS_RANK.get(status, -1) >= model.STATUS_RANK["Reviewed"]
        if path not in view.changed and not strict and uc not in raised:
            continue
        text = view.text(path)
        digest = hashlib.sha256((context_digest + (text or "")).encode("utf-8")).hexdigest()
        stored = cache.get(path)
        if not (isinstance(stored, list) and len(stored) == 4 and stored[0] == digest
                and type(stored[1]) is int and type(stored[2]) is int
                and isinstance(stored[3], str)):
            report = model.Reporter(view.root)
            notice = io.StringIO()
            checked = validate_use_case.validate_files([os.path.join(view.root, path)],
                                                      docs_dir=view.docs.root, report=report, stream=notice)
            if isinstance(checked, int):
                stored = [digest, 1, 0, notice.getvalue().splitlines()[0] if notice.getvalue() else "validation could not run"]
            else:
                first = next(("%(code)s: %(message)s" % f for f in checked.sorted() if f["severity"] == "ERROR"), "")
                stored = [digest, checked.count("ERROR"), checked.count("WARN"), first]
            cache[path] = stored
            slot["validated"] = dict(cache)
        _, errors, warnings, first = stored
        if errors or warnings:
            label = "- %s in %s: %d errors, %d warnings" % (uc, path, errors, warnings)
            if first:
                label += "; " + first.replace("\n", " ")
            if strict and errors:
                label += "; a problem at push"
            lines.append(label)
        if uc in raised:
            claim = raised[uc]
            lines.append("- %s: %s -> %s" % (uc, claim.before or "absent", claim.after))
    current_paths = {value[0] for value in current.values()}
    slot["validated"] = {path: value for path, value in cache.items() if path in current_paths}
    if lines:
        titles = _titles(view.root, docs_rel)
        lines = [model.with_titles(line, titles) for line in lines]
    return lines[:OPEN_LINES] + (["... %d more open items" % (len(lines) - OPEN_LINES)] if len(lines) > OPEN_LINES else [])


def _open_context(root, args, event, slot=None):
    import change_view
    session = event.session_id if event else None
    docs_rel = os.path.relpath(os.path.join(root, args.docs), root).replace(os.sep, "/")
    if slot is None:
        slot = snapshot_read(root, session) or {"validated": {}, "shown": None}
    view = change_view.view_for(root, getattr(args, "base", None), docs_rel)
    return slot, open_list(view, docs_rel, slot)


def turn_start(root, args, event):
    """Only the main thread saves caches; a timed-out worker never advances shown."""
    session = event.session_id if event else None
    docs_rel = os.path.relpath(os.path.join(root, args.docs), root).replace(os.sep, "/")
    slot = snapshot_read(root, session)
    box = []
    def compute():
        try:
            current = slot
            if current is None:
                # The first prompt supplies the baseline, within the same computation cap.
                snapshot_write(root, docs_rel, session)
                current = snapshot_read(root, session)
            if current is None:
                raise GateError("session snapshot unavailable")
            box.append(_open_context(root, args, event, slot=current))
        except BaseException as exc:
            box.append(exc)
    worker = threading.Thread(target=compute, daemon=True)
    worker.start()
    worker.join(TURN_START_SECONDS)
    if worker.is_alive():
        if slot is not None:
            try:
                _snapshot_save(root, session, update={"validated": slot["validated"]})
            except BaseException as exc:
                log(root, "turn-start", PASS, "capped cache save failed: %s" % exc)
        return Verdict(FAILED, "", "turn-start cap reached")
    if not box or isinstance(box[0], BaseException):
        return Verdict(FAILED, "", "open list failed: %s" % (box[0] if box else "no result"))
    slot, lines = box[0]
    digest = _list_digest(lines)
    if slot.get("shown") == digest:
        _snapshot_save(root, session, update={"validated": slot["validated"]})
        return Verdict(PASS, "", "open list unchanged")
    text = OPEN_HEADING + "\n" + "\n".join(lines) if lines else "Nothing is open now." if slot.get("shown") else ""
    _snapshot_save(root, session, update=dict(slot, shown=digest))
    return Verdict(PASS, text, "open list %d" % len(lines))


def session_start(root, args, event):
    docs_rel = os.path.relpath(os.path.join(root, args.docs), root).replace(os.sep, "/")
    session = event.session_id if event else None
    snapshot_write(root, docs_rel, session)
    try:
        import workflow_state
        output = io.StringIO()
        with redirect_stdout(output):
            state = workflow_state.collect(args.docs)
            if "migration" not in state:
                state["next"] = workflow_state.decide(state)
            workflow_state.print_text(state)
        lines = output.getvalue().strip().splitlines()
    except BaseException as exc:
        return could_not_run("workflow_state.py", exc)
    try:
        slot, opened = _open_context(root, args, event)
        extra = [OPEN_HEADING] + opened if opened else []
        _snapshot_save(root, session, update=dict(slot, shown=_list_digest(opened)))
    except BaseException as exc:
        log(root, "session-start", PASS, "open list failed: %s" % exc)
        extra = []
    # Budget includes the heading, cut notice, Next step tail and open-work list.
    budget = MAX_CONTEXT_LINES - 1 - len(extra)
    if len(lines) > budget:
        next_step = next((i for i, line in enumerate(lines) if line.startswith("Next step:")), len(lines))
        tail = lines[next_step:][:max(0, budget - 1)]
        head_count = max(0, budget - len(tail) - 1)
        lines = lines[:head_count] + ["... %d more lines: run workflow_state.py for the full state" %
                                     (len(lines) - head_count - len(tail))] + tail
    return Verdict(PASS, "Specification state of this repository:\n" + "\n".join(lines + extra), "")


def validation(paths, docs, error_result, heading):
    """Keep validation failures local and leave the full text for the profile."""
    if not paths:
        return Verdict(PASS, "", "")
    try:
        import spec_model
        import validate_use_case
        report = spec_model.Reporter(os.getcwd())
        notice = io.StringIO()
        with redirect_stdout(notice), redirect_stderr(notice):
            checked = validate_use_case.validate_files(paths, docs_dir=docs, report=report, local=True)
        if isinstance(checked, int):
            if checked == spec_model.OLD_FORMAT_EXIT:
                return Verdict(WARN, notice.getvalue().strip(), "OLD_FORMAT")
            return could_not_run("validate_use_case.py", GateError("unexpected result %s" % checked))
        edited = {os.path.abspath(path) for path in paths}
        checked.findings = [finding for finding in checked.findings
                            if finding["code"] not in ("REQUIREMENTS_LINE", "MECHANISM_TERM")
                            and not (finding["code"] in ("OLD_FORMAT", "UNREADABLE")
                                     and os.path.abspath(os.path.join(checked.root, finding["path"])) not in edited)]
        result = error_result if checked.count("ERROR") else WARN if checked.count("WARN") else PASS
        if result == PASS:
            return Verdict(PASS, "", "")
        checked.print_text(stream=notice)
        return Verdict(result, heading + "\n" + notice.getvalue().strip(), "")
    except BaseException as exc:
        return could_not_run("validate_use_case.py", exc)


def after_edit(root, args, event):
    try:
        base = event.cwd if event and event.cwd and os.path.isdir(event.cwd) else os.getcwd()
        paths = list(args.paths) + (event.paths if event else [])
        specs = specifications(root, base, args.docs, paths)
        verdict = validation(specs, args.docs, WARN,
                             "The specification just edited has findings, for information: "
                             "fix those that belong to your task.")
        return verdict._replace(detail=" ".join(specs or paths))
    except BaseException as exc:
        return could_not_run("selecting edited specifications", exc)


def open_records(view):
    """The changed change records that still exist in the working tree."""
    return sorted(name for name in view.changed
                  if view.kind(name) == "change_record"
                  and os.path.isfile(os.path.join(view.root, name)))


def forget(state):
    try:
        os.remove(state)
    except (OSError, TypeError):
        pass


def claim_check(view, args, event):
    """Select only locally owned raises and check their evidence against the shared view.

    Returns the drifts (one per claim without its evidence), the baseline's name and the open list's size."""
    import change_view
    import status_claims
    import spec_model as model
    docs_rel = os.path.relpath(os.path.join(view.root, args.docs), view.root).replace(os.sep, "/")
    slot = snapshot_read(view.root, event.session_id if event else None)
    code, head = git(view.root, "rev-parse", "--verify", "HEAD")
    own = set(change_view.ChangeView(view.root, change_view.Base(head.strip() if code == 0 else None,
                                                              "HEAD", "working tree"), docs_rel).changed)
    head_statuses = status_claims.statuses(view.root, docs_rel, "HEAD")
    current = status_claims.statuses(view.root, docs_rel)
    baseline, label = head_statuses, "HEAD"
    # Ownership belongs to the Status transition, independently of spill paths.
    transitions = status_claims.find_claims(head_statuses, current)
    snapshot_base = (slot and ((slot["head"] and
                     git(view.root, "merge-base", "--is-ancestor", slot["head"], "HEAD")[0] == 0)
                     or slot["head"] is None))
    if snapshot_base:
        baseline, label = slot["statuses"], "snapshot"
        revision = slot["head"] + "..HEAD" if slot["head"] else "HEAD"
        code, commits = git(view.root, "rev-list", revision, "--not", "--remotes")
        if code and not head.strip():
            code, commits = 0, ""
        if code:
            raise GateError("cannot read session commits")
        for commit in commits.splitlines():
            code, paths = git(view.root, "diff-tree", "--root", "--cc", "--no-commit-id", "--name-only", "-r", "-z", commit)
            if code:
                raise GateError("cannot read session commit paths")
            own.update(path for path in paths.split("\0") if path)
            code, parents = git(view.root, "rev-list", "--parents", "-n", "1", commit)
            if code:
                raise GateError("cannot read session commit parents")
            after = status_claims.statuses(view.root, docs_rel, commit)
            parent_statuses = [status_claims.statuses(view.root, docs_rel, parent)
                               for parent in parents.split()[1:]]
            # A merge inherits a remote raise when any parent already has that Status.
            before = {}
            for values in parent_statuses:
                for uc, value in values.items():
                    if model.STATUS_RANK.get(value[1], -1) > model.STATUS_RANK.get(before.get(uc, (None, None))[1], -1):
                        before[uc] = value
            transitions.extend(status_claims.find_claims(before, after))
    owned_ranks = {}
    for transition in transitions:
        owned_ranks[transition.uc] = max(owned_ranks.get(transition.uc, -1),
                                        model.STATUS_RANK[transition.after])
    drifts = []
    for claim in status_claims.find_claims(baseline, current):
        if model.STATUS_RANK[claim.after] > owned_ranks.get(claim.uc, -1):
            continue
        problems, warnings = status_claims.claim_problems(view, claim, docs_rel, spill=own)
        if problems:
            drifts.append(Drift(
                ("claim %s %s" % (claim.uc, claim.after),),
                "%s: %s -> %s without its evidence" % (claim.uc, claim.before or "absent", claim.after),
                ["- " + problem for problem in problems],
                "Add the evidence, or set the Status back to %s and tell the person what remains."
                % (claim.before or "Draft"),
                "%s raised to %s without its evidence" % (claim.uc, claim.after)))
    # This list reads docs only and is advisory, even when its validation fails.
    try:
        count = len(open_list(view, docs_rel, slot or {"validated": {}}))
    except BaseException as exc:
        log(view.root, "before-stop", PASS, "open list failed: %s" % exc)
        count = 0
    return drifts, label, count


def record_drifts(view):
    """One drift per change record changed in this change and still present: work not closed yet."""
    return [Drift(("record " + name,), "Open change record " + name,
                  ["- the change it records is in progress in this change"],
                  "Finish the change it records (up-7-implementing-use-cases), or tell the person it waits.",
                  "Open change record " + name)
            for name in open_records(view)]


def code_drift(view):
    """Behavior code changed without a specification change, a 'No behavior change:' line or a 'Fixes:' note:
    the spec-first guard's own reading (spec_model.read_change) of the change view, with the commit messages since
    the base. A light-path fix is no exception: it is asked once before its commit, like any other code, and the
    question says which answer fits it. Code that reaches the session through a pull or a merge is on the base, not
    in the change, so it is never asked as this session's drift. The hook has no --code patterns; a pipeline that
    passes them to the guard narrows only the guard."""
    import spec_model as model
    messages = ""
    if view.base.commit:
        code, messages = git(view.root, "log", "--format=%B", view.base.commit + "..HEAD")
        messages = messages if code == 0 else ""
    reading = model.read_change(view.changed, view.docs_rel, view.kind, messages)
    if not reading.code_without_spec():
        return []
    # One key per piece of work: the base's name and the branch, which stay put while the work is committed. The
    # base's commit does not: on the integration branch the merge base is HEAD, and with a remote it moves at
    # each push, so a key holding it would ask again after every commit.
    code, branch = git(view.root, "symbolic-ref", "-q", "--short", "HEAD")
    branch = branch.strip() if code == 0 and branch.strip() else "a detached HEAD"
    base = view.base.ref or view.base.commit or "none"
    return [Drift(("code without a specification since %s on %s" % (base, branch),),
                  "Code changed without a specification",
                  ["- %s in a commit message" % reading.summary(view.docs_rel)],
                  "Change the specification first (up-1-triaging-change-requests); when no behavior changes, "
                  "add the line 'No behavior change: UC-XXX' (or 'none' and the reason) to the commit message; "
                  "when the code fixes a bug against a clear specification (the light path), commit it with the note "
                  "'Fixes: UC-XXX BR-YYY' in this session: for a bug fixed against a clear specification, answer "
                  "\"at the end of the session\", not \"later\", which would record work that the commit closes.",
                  "Code changed without a specification: " + reading.shown())]


def a_files_drift(root):
    """The project's own A-files check, run as its documentation says (python3 tools/check_tracking.py --strict,
    or without --strict for an earlier check that does not know it): exit 0 is a clean shape, exit 1 with
    'path:line: ERROR CODE: message' lines a broken one. Anything else means the check could not run; that is
    logged and never fails the stop."""
    import spec_model as model
    path = os.path.join(root, "tools", "check_tracking.py")
    if not _uses_a_files(root) or not os.path.isfile(path):
        return []
    try:
        done = None
        # An earlier A-files check has no --strict (usage error, 2) and exits 1 on problems without it.
        for options in (["--strict"], []):
            done = subprocess.run([sys.executable, path, "--root", root] + options, cwd=root, capture_output=True,
                                  text=True, errors="replace", timeout=A_FILES_TIMEOUT_SECONDS)
            if done.returncode != 2:
                break
    except (OSError, subprocess.SubprocessError) as exc:
        log(root, "before-stop", PASS, "A-files check could not run: %s: %s" % (type(exc).__name__, exc))
        return []
    findings = [match for match in map(A_FILES_FINDING.match, done.stdout.splitlines()) if match]
    if done.returncode == 0:
        return []
    if done.returncode != 1 or not findings:
        last = (done.stderr.strip().splitlines() or ["no output"])[-1]
        log(root, "before-stop", PASS, "A-files check could not run: exit %d: %s" % (done.returncode, last))
        return []
    findings.sort(key=lambda found: (found["path"], int(found["line"]), found["code"]))
    lines = ["- " + found.group(0) for found in findings[:A_FILES_LINES]]
    if len(findings) > A_FILES_LINES:
        lines.append("- ... %d more: run python3 tools/check_tracking.py" % (len(findings) - A_FILES_LINES))
    keys = tuple(sorted({a_files_key(found) for found in findings}))
    return [Drift(keys, "The A-files' shape is broken", lines,
                  "Fix what the A-files check reports (python3 tools/check_tracking.py).",
                  "Fix the shape of the A-files (python3 tools/check_tracking.py)")]


def _uses_a_files(root):
    """The project uses the A-files: ACTIVE.md holds the hot-zone marker. An ACTIVE.md that cannot be decoded counts
    when its bytes hold the marker, so that the check reports it as unreadable instead of the gate going silent."""
    import spec_model as model
    if model.a_files_present(root):
        return True
    try:
        with open(os.path.join(root, "ACTIVE.md"), "rb") as handle:
            return model.A_FILES_MARKER.encode("utf-8") in handle.read()
    except OSError:
        return False


def a_files_key(found):
    """A finding's identity: its path, its code and the subject its message names, never its line number or its
    problem text, which carry counts and positions that change while the finding stays the same."""
    subject = " ".join(A_FILES_SUBJECT.findall(found["message"]))
    return ("A-files %s %s %s" % (found["path"], found["code"], subject)).rstrip()


def _asked_fallback(root, session):
    """A file outside the git folder, for a session whose git folder cannot be written."""
    key = hashlib.sha256((os.path.realpath(root) + "\0" + (session or "")).encode("utf-8")).hexdigest()
    return os.path.join(tempfile.gettempdir(), ASKED_FALLBACK_PREFIX + key[:FALLBACK_KEY_DIGITS] + ".json")


def _fallback_asked(root, session) -> set:
    """The drift keys the fallback file holds; none when it is missing or unreadable. It holds a list of keys, as
    upspec 1.3.0 wrote it; a file of the commit 0646b0c holds them under "asked", beside a HEAD no longer read."""
    try:
        with open(_asked_fallback(root, session), encoding="utf-8") as handle:
            stored = json.load(handle)
    except (OSError, ValueError, UnicodeError):
        return set()
    if isinstance(stored, dict):
        stored = stored.get("asked")
    return {key for key in stored if isinstance(key, str)} if isinstance(stored, list) else set()


def asked_keys(root, session) -> set:
    """The drifts already asked in this session: the snapshot's list and the fallback file's."""
    return set((snapshot_read(root, session) or {}).get("asked", [])) | _fallback_asked(root, session)


def remember_asked(root, session, docs_rel, keys) -> bool:
    """Record the asked drifts in the session snapshot, else in the fallback file; False when neither holds them."""
    try:
        if snapshot_read(root, session) is None:
            # A stop before any session start: HEAD's Statuses keep the claim baseline what it was.
            _snapshot_save(root, session, docs_rel=docs_rel, baseline="HEAD")
        _snapshot_save(root, session, update={"asked": list(keys)})
        if set(keys) <= set((snapshot_read(root, session) or {}).get("asked", [])):
            return True
    except BaseException as exc:
        log(root, "before-stop", PASS, "snapshot write failed: %s" % exc)
    try:
        stored = _fallback_asked(root, session)
        with open(_asked_fallback(root, session), "w", encoding="utf-8") as handle:
            json.dump(sorted(stored | set(keys)), handle)
    except (OSError, TypeError, ValueError):
        return False
    _prune_fallbacks()
    return True


def _prune_fallbacks():
    """Remove the fallback files of sessions that ended: untouched for longer than SNAPSHOT_TEMP_MAX_AGE_SECONDS,
    the age past which a session's temporary writes are abandoned. Nothing else in the temporary folder is read."""
    name = re.compile(re.escape(ASKED_FALLBACK_PREFIX) + r"[0-9a-f]{%d}\.json" % FALLBACK_KEY_DIGITS)
    folder = tempfile.gettempdir()
    try:
        with os.scandir(folder) as found:
            entries = [entry for entry in found if name.fullmatch(entry.name)]
    except OSError:
        return
    for entry in entries:
        try:
            if (entry.is_file(follow_symlinks=False)
                    and time.time() - entry.stat(follow_symlinks=False).st_mtime > SNAPSHOT_TEMP_MAX_AGE_SECONDS):
                os.remove(entry.path)
        except OSError:
            continue


def _gate_command(root):
    """How the agent runs this gate from the repository's root."""
    here = os.path.join(HERE, "hook_gate.py")
    try:
        relative = os.path.relpath(os.path.realpath(here), os.path.realpath(root))
    except ValueError:          # another drive
        relative = here
    return "python3 " + shlex.quote(here if relative.startswith("..") else relative.replace(os.sep, "/"))


def question(root, drifts, titles=None) -> str:
    """One question per drift, with what each answer means and the command that records 'later'. The drifts' keys keep
    the bare identifiers; only the text a person reads carries their titles."""
    import spec_model as model
    titles = titles or {}
    where = ("as an item in AHEAD.md" if later_destination(root) else
             "as a line in %s in the git folder, listed with the open work at session start" % DEFERRED_NAME)
    lines = [QUESTION_HEADING,
             "- now: align it in this session, as the item says;",
             "- end of the session: leave it for now and remind the person of it once, when the session ends;",
             "- later: run the item's Later command, which records it %s, then go on." % where,
             QUESTION_CLOSING]
    command = _gate_command(root)
    for number, drift in enumerate(drifts, 1):
        lines.append("")
        lines.append("%d. %s" % (number, model.with_titles(drift.title, titles)))
        lines.extend(model.with_titles(line, titles) for line in drift.detail)
        lines.append("To align: " + model.with_titles(drift.align, titles))
        lines.append("Later: %s later %s" % (command, shlex.quote(model.with_titles(drift.later_text, titles))))
    return "\n".join(lines)


def before_stop(view, args, event) -> Verdict:
    """Ask once per drift; a drift asked before in this session, and a stop without drift, pass quietly."""
    session = event.session_id if event else None
    docs_rel = os.path.relpath(os.path.join(view.root, args.docs), view.root).replace(os.sep, "/")
    drifts, label, count = claim_check(view, args, event)
    drifts += record_drifts(view) + code_drift(view) + a_files_drift(view.root)
    asked = asked_keys(view.root, session)
    new = []
    for drift in drifts:
        if not set(drift.keys) <= asked:
            new.append(drift)
            asked |= set(drift.keys)
    detail = "baseline %s; open list %d; drifts %d, new %d" % (label, count, len(drifts), len(new))
    if not new:
        return Verdict(PASS, "", detail)
    text = question(view.root, new, _titles(view.root, docs_rel))
    if not remember_asked(view.root, session, docs_rel, [key for drift in new for key in drift.keys]):
        # Asking again at every turn would keep the agent working: without a memory it only informs.
        return Verdict(WARN, "The gate cannot remember what it asked, so it does not ask; for information:\n\n"
                       + text, detail + "; not remembered")
    return Verdict(ASK, text, detail)


# --- later: a drift the person chose to align later ---

def deferred_items(root) -> list:
    """The deferred list's items, newest last: a DeferredItem for each '- DATE TEXT' line."""
    path = git_path(root, DEFERRED_NAME)
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except (OSError, TypeError, UnicodeError):
        return []
    items = []
    for line in lines:
        match = re.match(r"^- (\d{4}-\d{2}-\d{2}) (.+)$", line.strip())
        if match:
            items.append(DeferredItem(match.group(1), match.group(2)))
    return items


def _ahead_plan(lines) -> Optional[AheadPlan]:
    """Where an item goes in AHEAD.md, or None when the layout is unknown.

    The index is the table above the hot zone's end whose header has ID and State; the entry goes at the end
    of the Items section below it."""
    import spec_model as model
    marker = next((n for n, line in enumerate(lines) if line.strip() == model.A_FILES_MARKER), None)
    if marker is None:
        return None
    for number in range(marker):
        cells = [cell.strip() for cell in lines[number].strip().strip("|").split("|")]
        if (lines[number].lstrip().startswith("|") and "ID" in cells and "State" in cells
                and number + 1 < marker and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[number + 1])):
            row = number + 2
            while row < marker and lines[row].lstrip().startswith("|"):
                row += 1
            items = next((n for n in range(marker, len(lines)) if lines[n].strip() == "## Items"), None)
            if items is None:
                return None
            entry = next((n for n in range(items + 1, len(lines)) if lines[n].startswith("## ")), len(lines))
            return AheadPlan(row, cells, entry)
    return None


def later_destination(root):
    """'AHEAD.md' when the project uses the A-files and its AHEAD.md can take an item, else None."""
    import spec_model as model
    if not model.a_files_present(root):
        return None
    try:
        lines = model.read_lines(os.path.join(root, "AHEAD.md"))
    except (OSError, UnicodeDecodeError):
        return None
    if model.a_file_home(root, lines) or _ahead_plan(lines) is None:
        return None
    return "AHEAD.md"


# What 'later' writes into AHEAD.md, as pairing contract row P9 states it: an index row with the next free
# identifier, the drift as its title, kind idea, state open and a dash in every other column; an entry under
# Items with What (the drift), Why (the person chose to align it later, with the date) and Write-up none.
LATER_ROW = {"Kind": "idea", "State": "open"}
LATER_ENTRY = ("- **What:** {text}",
               "- **Why:** the person chose to align it later when an agent's turn ended ({date})",
               "- **Write-up:** none")


def record_later(root, text) -> str:
    """Record the drift where later_destination says; return what was written. A drift recorded before (the same
    text in an AHEAD entry's What, or a line of the deferred list) is not recorded again."""
    import spec_model as model
    text = " ".join(text.split())
    today = datetime.date.today().isoformat()
    if later_destination(root):
        path = os.path.join(root, "AHEAD.md")
        lines = model.read_lines(path)
        plan = _ahead_plan(lines)
        what = LATER_ENTRY[0].format(text=text)
        for number, line in enumerate(lines):
            if line.strip() == what:
                heading = next((lines[n] for n in range(number, -1, -1) if lines[n].startswith("### ")), "")
                found = model.RE_AH_ID.search(heading)
                return "Recorded already%s in AHEAD.md; nothing added." % (" as " + found.group(0) if found else "")
        numbers = [int(found[3:]) for found in model.RE_AH_ID.findall("\n".join(lines))]
        identifier = "AH-%03d" % (max(numbers, default=0) + 1)
        title = text.replace("|", "/")
        values = dict(LATER_ROW, ID=identifier, Title=title)
        new_row = "| " + " | ".join(values.get(cell, "—") for cell in plan.header) + " |"
        row, entry = plan.row, plan.entry
        start = entry
        while start > 0 and not lines[start - 1].strip():
            start -= 1
        block = ["", "### %s %s" % (identifier, title), ""] + [field.format(text=text, date=today)
                                                                for field in LATER_ENTRY]
        lines = lines[:start] + block + ([""] if start < len(lines) and start == entry else []) + lines[start:]
        lines = lines[:row] + [new_row] + lines[row:]
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))
        return "Recorded as %s in AHEAD.md." % identifier
    path = git_path(root, DEFERRED_NAME)
    if path is None:
        raise GateError("cannot locate the git folder")
    if any(item.text == text for item in deferred_items(root)):
        return "Recorded already in %s; nothing added." % path
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("- %s %s\n" % (today, text))
    return "Recorded in %s; it is listed with the open work at session start until its line is removed." % path


def later_main(words) -> int:
    """hook_gate.py later TEXT: run by the agent when the person answers 'later'."""
    text = " ".join(words).strip()
    if not text or text.startswith("-"):
        print("usage: hook_gate.py later TEXT (the drift to align later)", file=sys.stderr)
        return 2
    try:
        root = find_root()
        print(record_later(root, text))
        return 0
    except (GateError, OSError, UnicodeError) as exc:
        print("hook_gate later: %s" % exc, file=sys.stderr)
        return 3


def log(root, mode, verdict, detail):
    """Append one line per firing to the git folder's log; keep the newest LOG_LINES."""
    path = git_path(root, LOG_NAME)
    if not path:
        return
    line = "%s %s exit=%d %s" % (datetime.datetime.now().isoformat(timespec="seconds"), mode, verdict, detail[:200])
    try:
        kept = []
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as handle:
                kept = handle.read().splitlines()[-(LOG_LINES - 1):]
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(kept + [line.rstrip()]) + "\n")
    except OSError:
        pass


class GateParser(argparse.ArgumentParser):
    def error(self, message):
        raise GateError(message)


def find_root(event=None):
    """Try the process directory, then the normalized event's two fallbacks."""
    starts = [os.getcwd()]
    if event:
        starts.extend(start for start in (event.cwd, event.workspace) if start)
    for start in starts:
        try:
            return repo_root(start)
        except (GateError, OSError):
            continue
    raise GateError("not inside a git repository: %s" % starts[0])


def main(argv):
    if argv and argv[0] == "later":
        # Not a hook moment: the agent runs it when the person answers 'later'.
        sys.path.insert(0, HERE)
        return later_main(argv[1:])
    parser = GateParser(description="One entry point for the agent hooks.")
    parser.add_argument("mode", choices=MODES)
    parser.add_argument("paths", nargs="*", help="after-edit: the edited files, besides those in the tool's JSON")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--base", help="before-stop: the branch a change starts from")
    parser.add_argument("--emit", default="raw", help="raw, claude, codex, antigravity or kiro (default: raw)")
    parse_problem = None
    try:
        args = parser.parse_args(argv)
    except GateError as exc:
        parse_problem = str(exc)
        # Retain a requested valid profile even when another argument is invalid.
        output_parser = GateParser(add_help=False)
        output_parser.add_argument("--emit", default="raw")
        try:
            args, _ = output_parser.parse_known_args(argv)
        except GateError:
            args = argparse.Namespace(emit="raw")
        args.mode = next((word for word in argv if word in MODES), "before-stop")
    except SystemExit as exc:
        return PASS if exc.code == 0 else FAILED
    sys.path.insert(0, HERE)
    try:
        import hook_profiles
    except BaseException as exc:
        try:
            log(find_root(), args.mode, PASS, "hook_profiles.py could not load: %s: %s" % (type(exc).__name__, exc))
        except BaseException:
            pass
        return PASS
    root, view, event = None, None, None
    profile = args.emit if args.emit in hook_profiles.PROFILES else "raw"
    try:
        problem = bundle_problem(HERE)
        if problem:
            raise GateError(problem)
        if parse_problem:
            raise GateError(parse_problem)
        payload = read_stdin()
        if args.mode == "turn-start" and not isinstance(payload, dict):
            raise GateError("turn-start payload is missing or invalid")
        event = hook_profiles.read_event(payload)
        # Relative edited paths retain their original base across the root chdir.
        if not event.cwd:
            event = event._replace(cwd=os.getcwd())
        root = find_root(event)
        os.chdir(root)
        if args.emit not in hook_profiles.PROFILES:
            raise GateError("unknown hook profile: %s" % args.emit)
        args.docs = args.docs or docs_folder(root)
        import spec_model as model
        warning = io.StringIO()
        # Any stop (5, or 1 for an unreadable file) becomes a warning; the hook never fails on it.
        stop = (model.stop_if_old(model.Docs(os.path.join(root, args.docs)), stream=warning, strict=True)
                if args.mode in ("session-start", "before-stop") else None)
        if stop:
            verdict = Verdict(WARN, warning.getvalue().rstrip(),
                              "OLD_FORMAT" if stop == model.OLD_FORMAT_EXIT else "UNREADABLE")
        elif args.mode == "before-stop":
            import change_view
            docs_rel = os.path.relpath(os.path.join(root, args.docs), root).replace(os.sep, "/")
            view = change_view.view_for(root, args.base, docs_rel)
            verdict = before_stop(view, args, event)
        elif args.mode == "turn-start":
            verdict = turn_start(root, args, event)
        elif args.mode == "session-start":
            verdict = Verdict(*session_start(root, args, event))
        else:
            verdict = Verdict(*after_edit(root, args, event))
    except BaseException as exc:
        verdict = Verdict(FAILED, "hook_gate: %s: %s" % (type(exc).__name__, exc), "")
    if root is None:
        try:
            root = find_root(event)
        except (GateError, OSError):
            pass
    if args.mode == "turn-start" and verdict.result != PASS:
        if root:
            log(root, args.mode, PASS, verdict.detail or verdict.text)
        return PASS
    report_saved = False
    if root:
        base_detail = ("base %s (%s)" % (view.base.ref, view.base.source)
                       if view is not None and view.base.ref else "base none")
        detail = base_detail + ("; " + verdict.detail if verdict.detail else "")
        full_message = hook_profiles.message(profile, args.mode, verdict.result, verdict.text)
        if len(full_message) > hook_profiles.message_cap(profile, args.mode):
            try:
                path = git_path(root, "up-hooks-report.txt")
                if path is None:
                    raise OSError("cannot locate the git folder")
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(full_message)
                report_saved = True
            except (OSError, UnicodeError) as exc:
                detail = "%s; could not write up-hooks-report.txt: %s%s" % (
                    base_detail, exc, "; " + verdict.detail if verdict.detail else "")
        log(root, args.mode, verdict.result, detail)
    output = hook_profiles.render(profile, args.mode, verdict.result, verdict.text, report_saved=report_saved)
    sys.stdout.write(output.stdout)
    sys.stderr.write(output.stderr)
    return output.code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
