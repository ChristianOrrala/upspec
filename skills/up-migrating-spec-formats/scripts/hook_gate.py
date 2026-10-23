#!/usr/bin/env python3
"""One entry point for the agent hooks, whatever tool calls it.

    hook_gate.py session-start [--docs DIR]
        the state of the specifications, as context for a new session
    hook_gate.py after-edit [PATH ...] [--docs DIR]
        the validator on every use case specification among the edited files
    hook_gate.py before-stop [--docs DIR] [--base REF]
        check only the session's Status claims for their evidence
    hook_gate.py turn-start [--docs DIR]
        changed open-work context, always non-blocking

Every moment accepts --emit raw|claude|codex|antigravity|kiro (default: raw).
A profile renders the internal result for the calling tool.

Edited paths come from the arguments and from the JSON the tool writes to
stdin: every string under a key that names a file path, and the file names on
the "*** Update File:", "*** Add File:" and "*** Move to:" lines of a patch body. Paths that
belong to the session (transcript, working directory, workspace) are ignored,
and a relative path is read from the session's directory when the JSON names
one. A change record is never taken for a specification, even when its name
starts with a use case's identifier.

Open records and specification findings are work in progress shown as context,
not stop conditions. The stop checks only locally owned Status raises against
this session's snapshot (or HEAD without one). Turn start reuses validation
and prints a changed open-work list within a short wall-clock cap.

The result is the same for every tool; the tool's hook configuration maps it:

    0  pass; text on stdout, if any, is context to add
    1  warn; show the text, do not block
    2  act; block, or keep the agent working, with the text as the reason
    3  the gate could not run (no git repository, a script missing, bad
       usage); never block on it

before-stop gives up at the third blocked stop without a fall in problem count,
or at the sixth consecutive block, and delivers the instruction to stop and report once
for the same problem set. Every firing appends one line to up-hooks.log in the repository's git
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
import subprocess
import sys
import threading
import tempfile
import time

# the release these copies belong to; hook_gate.py refuses siblings of another release
UPSPEC_VERSION = "1.2.0"

sys.dont_write_bytecode = True   # a __pycache__ folder in tools/specs/ would be an unexplained file in every change

HERE = os.path.dirname(os.path.abspath(__file__))
UC_ID = re.compile(r"\bUC-\d{3}\b")
STDIN_WAIT = 1.0                # seconds: hook runners write their JSON at once; a terminal never writes
# Three blocked stops without fewer distinct problems mean the agent should stop and report.
NO_PROGRESS_STOPS = 3
# Below Claude Code and Copilot CLI's eight, two no-progress windows, and the only loop end in Codex and Antigravity.
BLOCK_CAP = 6
MAX_CONTEXT_LINES = 60          # a longer state report is cut; the full one is one command away
LOG_LINES = 200                 # a proof session and some days of work; older lines are dropped
LOG_NAME = "up-hooks.log"
STATE_NAME = "up-hook-stop"
PASS, WARN, ACT, FAILED = 0, 1, 2, 3
MODES = ("session-start", "after-edit", "before-stop", "turn-start")
# Each session owns one git-folder JSON file, separate from the stop loop guard.
SESSION_PREFIX = "up-session-"
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
OPEN_HEADING = ("Work in progress: fix an item only when it belongs to the current task. "
                "Do not mark a use case Implemented or Tested until its items are clean; the push check enforces this.")
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
    give_up: bool = False


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


def _snapshot_save(root, session, update=None, docs_rel=None):
    """Atomically replace only this session's slot, then prune older session files."""
    import status_claims
    path = _snapshot_path(root, session)
    slot = snapshot_read(root, session)
    if slot is None:
        if docs_rel is None:
            return
        code, head = git(root, "rev-parse", "--verify", "HEAD")
        slot = {"session": session, "time": datetime.datetime.now().isoformat(),
                "head": head.strip() if code == 0 else None,
                "statuses": status_claims.statuses(root, docs_rel), "shown": None, "validated": {}}
    if update:
        # Cache updates must preserve the session's original baseline.
        slot.update({key: update[key] for key in ("shown", "validated") if key in update})
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
                and isinstance(slot["validated"], dict)):
            return slot
    except (OSError, ValueError, TypeError, UnicodeError):
        pass
    return None


def _list_digest(lines):
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def open_list(view, docs_rel, slot) -> list[str]:
    """Read git paths and docs only; reuse validation while its inputs stay unchanged."""
    import spec_model as model
    import status_claims
    import validate_use_case
    lines = ["- Open change record: " + name for name in open_records(view)]
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
            label = "- %s (%s): %d errors, %d warnings" % (uc, path, errors, warnings)
            if first:
                label += "; " + first.replace("\n", " ")
            if strict and errors:
                label += "; fails at push"
            lines.append(label)
        if uc in raised:
            claim = raised[uc]
            lines.append("- %s: %s -> %s" % (uc, claim.before or "absent", claim.after))
    current_paths = {value[0] for value in current.values()}
    slot["validated"] = {path: value for path, value in cache.items() if path in current_paths}
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
        verdict = validation(specs, args.docs, ACT,
                             "The specification just edited has findings; fix them before going on:")
        return verdict._replace(detail=" ".join(specs or paths))
    except BaseException as exc:
        return could_not_run("selecting edited specifications", exc)


def open_records(view):
    """The changed change records that still exist in the working tree."""
    return sorted(name for name in view.changed
                  if view.kind(name) == "change_record"
                  and os.path.isfile(os.path.join(view.root, name)))


def problem_ids(text: str) -> list[str]:
    """Identify list problems and validator findings, without headings or line numbers."""
    found = set()
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("- "):
            found.add(line)
        else:
            finding = re.match(r"^(.+?):\d+: ((?:ERROR|WARN|INFO) \S+ \[[^\]]*\]: .*)$", line)
            if finding:
                found.add("%s: %s" % finding.groups())
    return sorted(found)


def fallback_state(root):
    """A repository-specific guard when its git folder is read-only."""
    key = hashlib.sha256(os.path.realpath(root).encode("utf-8")).hexdigest()
    return os.path.join(tempfile.gettempdir(), STATE_NAME + "-" + key)


def guard(state_path: str, session: Optional[str], ids: list[str]) -> str:
    """Persist a blocked stop; raise OSError when the caller must try fallback storage."""
    # Version 2 distinguishes the count window and delivered ids from the old digest state.
    state = {"version": 2, "session": session, "counts": [], "blocks": 0, "given_up": None}
    try:
        with open(state_path, encoding="utf-8") as handle:
            previous = json.load(handle)
        if (isinstance(previous, dict) and set(previous) == set(state)
                and type(previous["version"]) is int and previous["version"] == 2
                and previous["session"] == session
                and type(previous["blocks"]) is int and 0 <= previous["blocks"] < BLOCK_CAP
                and isinstance(previous["counts"], list)
                and len(previous["counts"]) == min(previous["blocks"], NO_PROGRESS_STOPS)
                and all(type(count) is int and count >= 0 for count in previous["counts"])
                and (previous["given_up"] is None or
                     (isinstance(previous["given_up"], list) and
                      all(isinstance(item, str) for item in previous["given_up"])))):
            state = previous
    except (OSError, TypeError, ValueError, KeyError, UnicodeError):
        pass
    ids = sorted(set(ids))
    if state["given_up"] is not None and set(state["given_up"]) == set(ids):
        return "quiet"
    state["given_up"] = None
    state["blocks"] += 1
    state["counts"] = (state["counts"] + [len(ids)])[-NO_PROGRESS_STOPS:]
    counts = state["counts"]
    give_up = (state["blocks"] >= BLOCK_CAP or
               (len(counts) == NO_PROGRESS_STOPS and counts[-1] >= counts[0]))
    if give_up:
        state.update(counts=[], blocks=0, given_up=ids)
    try:
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
    except (OSError, TypeError) as exc:
        raise OSError("cannot write loop guard state") from exc
    return "give_up" if give_up else "block"


def guard_reset(state_path):
    """Forget both the blocked-stop counts and any previously delivered give-up."""
    forget(state_path)


def forget(state):
    try:
        os.remove(state)
    except (OSError, TypeError):
        pass


def claim_check(view, args, event):
    """Select only locally owned raises and check their evidence against the shared view."""
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
    reports = []
    for claim in status_claims.find_claims(baseline, current):
        if model.STATUS_RANK[claim.after] > owned_ranks.get(claim.uc, -1):
            continue
        problems, warnings = status_claims.claim_problems(view, claim, docs_rel, spill=own)
        if problems:
            reports.append("%s: %s -> %s\n%s\nAdd the evidence, or set the Status back to %s and tell the person what remains." %
                           (claim.uc, claim.before or "absent", claim.after,
                            "\n".join("- " + problem for problem in problems), claim.before or "Draft"))
    # This list reads docs only and is advisory, even when its validation fails.
    try:
        count = len(open_list(view, docs_rel, slot or {"validated": {}}))
    except BaseException as exc:
        log(view.root, "before-stop", PASS, "open list failed: %s" % exc)
        count = 0
    return Verdict(ACT if reports else PASS, "\n\n".join(reports), "baseline %s; open list %d" % (label, count))


def before_stop(view, args, event) -> Verdict:
    combined = claim_check(view, args, event)
    state, fallback = git_path(view.root, STATE_NAME), fallback_state(view.root)
    if combined.result in (PASS, WARN):
        guard_reset(state)
        guard_reset(fallback)
    if combined.result != ACT:
        return combined
    ids = problem_ids(combined.text)
    session = event.session_id if event else None
    try:
        outcome = guard(state, session, ids)
    except OSError:
        try:
            outcome = guard(fallback, session, ids)
        except OSError:
            return combined._replace(result=WARN, text="the loop guard cannot store its state; not blocking\n\n" + combined.text)
    else:
        guard_reset(fallback)
    if outcome == "give_up":
        return combined._replace(result=WARN, give_up=True,
                                 text="The Status claims still lack evidence and the same problems came back.\n\n" + combined.text)
    if outcome == "quiet":
        return combined._replace(result=WARN)
    return combined._replace(text="The Status claims lack evidence. Fix these problems before you stop, "
                             "or say which one cannot be fixed and why:\n\n" + combined.text)


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
        stop = (model.stop_if_old(model.Docs(os.path.join(root, args.docs)), stream=warning)
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
        full_message = hook_profiles.message(profile, args.mode, verdict.result, verdict.text, verdict.give_up)
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
    output = hook_profiles.render(profile, args.mode, verdict.result, verdict.text, verdict.give_up, report_saved=report_saved)
    sys.stdout.write(output.stdout)
    sys.stderr.write(output.stderr)
    return output.code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
