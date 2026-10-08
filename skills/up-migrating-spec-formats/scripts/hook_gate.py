#!/usr/bin/env python3
"""One entry point for the agent hooks, whatever tool calls it.

    hook_gate.py session-start [--docs DIR]
        the state of the specifications, as context for a new session
    hook_gate.py after-edit [PATH ...] [--docs DIR]
        the validator on every use case specification among the edited files
    hook_gate.py before-stop [--docs DIR] [--base REF]
        the finish check for every change record still open

Edited paths come from the arguments and from the JSON the tool writes to
stdin: every string under a key that names a file path, and the file names on
the "*** Update File:", "*** Add File:" and "*** Move to:" lines of a patch body. Paths that
belong to the session (transcript, working directory, workspace) are ignored,
and a relative path is read from the session's directory when the JSON names
one. A change record is never taken for a specification, even when its name
starts with a use case's identifier.

A change record is open when it is added or changed and not committed, or
changed on the current branch since it left the base branch (--base, else the
environment variable UP_BASE, else the remote default branch, origin/main, main, origin/master, master).
Once the change touches files outside the specification folder and tools/specs/,
the finish check runs against the commit where the branch left its base.
During triage, specification writing and review it waits for implementation.

The result is the same for every tool; the tool's hook configuration maps it:

    0  pass; text on stdout, if any, is context to add
    1  warn; show the text, do not block
    2  act; block, or keep the agent working, with the text as the reason
    3  the gate could not run (no git repository, a script missing, bad
       usage); never block on it

before-stop answers 1 instead of 2 when the same problems come back for the
third time in a row, so that an agent that cannot fix them stops and reports
them. Every firing appends one line to up-hooks.log in the repository's git
folder: the evidence that a hook fires.

The scripts it calls must sit in its own folder: workflow_state.py,
validate_use_case.py, and finish_change.py with scope_audit.py,
uc_change_list.py, unrecorded_changes.py and spec_model.py.
scaffold_docs.py --hooks copies them together into tools/specs/.

Requires Python 3.9+, standard library only, and git.
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import threading
import tempfile

sys.dont_write_bytecode = True   # a __pycache__ folder in tools/specs/ would be an unexplained file in every change

HERE = os.path.dirname(os.path.abspath(__file__))
NO_BYTECODE = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
UC_ID = re.compile(r"\bUC-\d{3}\b")
SPEC_NAME = re.compile(r"^UC-\d{3}\b.*\.md$")
PATH_KEY = re.compile(r"(^|_)(file_?path|path|paths|target_?file|filename)$", re.IGNORECASE)
SESSION_KEY = re.compile(r"transcript|cwd|dir|workspace", re.IGNORECASE)
PATCH_FILE = re.compile(r"^\*\*\* (?:(?:Update|Add) File|Move to): (.+)$", re.MULTILINE)
SUMMARY = re.compile(r"(\d+) errors?, (\d+) warnings?")
BASES = ("origin/main", "main", "origin/master", "master")
STDIN_WAIT = 1.0                # seconds: hook runners write their JSON at once; a terminal never writes
REPEATS_BEFORE_GIVING_UP = 2    # the same problems blocked twice; the third time the agent may stop and report
MAX_CONTEXT_LINES = 60          # a longer state report is cut; the full one is one command away
MAX_MESSAGE_CHARS = 9000        # below the smallest cap on hook output among the tools checked (10,000 characters)
LOG_LINES = 200                 # a proof session and some days of work; older lines are dropped
LOG_NAME = "up-hooks.log"
STATE_NAME = "up-hook-stop"
PASS, WARN, ACT, FAILED = 0, 1, 2, 3
MODES = ("session-start", "after-edit", "before-stop")


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


def run_script(root, name, *args):
    path = os.path.join(HERE, name)
    if not os.path.isfile(path):
        raise GateError("%s is missing next to hook_gate.py; copy the scripts with scaffold_docs.py --hooks" % name)
    done = subprocess.run([sys.executable, path] + list(args), cwd=root, capture_output=True, text=True,
                          env=NO_BYTECODE)
    return done.returncode, done.stdout.strip(), done.stderr.strip()


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


def payload_paths(node):
    """Every path a hook payload names as an edited file."""
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            key = str(key)
            if SESSION_KEY.search(key):
                continue
            if PATH_KEY.search(key) and isinstance(value, str):
                found.append(value)
            elif PATH_KEY.search(key) and isinstance(value, list):
                found.extend(item for item in value if isinstance(item, str))
            else:
                found.extend(payload_paths(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(payload_paths(item))
    elif isinstance(node, str):
        found.extend(name.strip() for name in PATCH_FILE.findall(node))
    return found


def specifications(root, base, docs, paths):
    """The use case specifications among the paths, relative to the root."""
    real_root = os.path.realpath(root)
    sys.path.insert(0, HERE)
    import spec_model
    use_case_dir = spec_model.Docs(os.path.join(root, docs)).use_case_dir
    if not use_case_dir:
        return []
    use_case_dir = os.path.realpath(use_case_dir)
    found = set()
    for path in paths:
        full = os.path.realpath(path if os.path.isabs(path) else os.path.join(base, path))
        try:
            rel = os.path.relpath(full, real_root).replace(os.sep, "/")
        except ValueError:          # another drive
            continue
        parts = rel.split("/")
        if parts[0] == ".." or "change-records" in parts or not SPEC_NAME.match(parts[-1]):
            continue
        if os.path.commonpath([full, use_case_dir]) == use_case_dir and os.path.isfile(full):
            found.add(rel)
    return sorted(found)


def cut(text, limit=MAX_MESSAGE_CHARS):
    """Keep a message under what tools pass on to the agent."""
    if len(text) <= limit:
        return text
    return text[:limit].rsplit("\n", 1)[0] + "\n... cut here; run the check by hand for the full report"


def session_start(root, args, payload):
    code, out, err = run_script(root, "workflow_state.py", "--docs", args.docs)
    if code != 0:
        raise GateError("workflow_state.py failed: %s" % (err or out))
    lines = out.splitlines()
    if len(lines) > MAX_CONTEXT_LINES:
        next_step = next((i for i, line in enumerate(lines) if line.startswith("Next step:")), len(lines))
        tail = lines[next_step:]
        head_count = max(0, MAX_CONTEXT_LINES - len(tail))
        head_count = min(head_count, next_step)
        rest = next_step - head_count
        lines = lines[:head_count] + ["... %d more lines: run workflow_state.py for the full state" % rest] + tail
    return PASS, cut("Specification state of this repository:\n" + "\n".join(lines)), ""


def after_edit(root, args, payload):
    session_dir = payload.get("cwd") if isinstance(payload, dict) else None
    base = session_dir if isinstance(session_dir, str) and os.path.isdir(session_dir) else os.getcwd()
    paths = list(args.paths) + (payload_paths(payload) if payload is not None else [])
    specs = specifications(root, base, args.docs, paths)
    if not specs:
        return PASS, "", " ".join(paths)
    code, out, err = run_script(root, "validate_use_case.py", "--docs", args.docs, *specs)
    if code not in (0, 1):
        raise GateError("validate_use_case.py failed: %s" % (err or out))
    summary = SUMMARY.search(out)
    errors = int(summary.group(1)) if summary else 0
    warnings = int(summary.group(2)) if summary else 0
    detail = " ".join(specs)
    if code == 0 and not warnings:
        return PASS, "", detail
    verdict = ACT if code == 1 or errors else WARN
    return verdict, cut("The specification just edited has findings; fix them before going on:\n" + out), detail


def base_commit(root, wanted):
    """The commit where the current branch left its base, or None when no base is known."""
    ref = wanted or os.environ.get("UP_BASE")
    if ref:
        code, fork = git(root, "merge-base", "HEAD", ref)
        if code:
            raise GateError("unknown base branch '%s': pass --base with a branch that exists" % ref)
        return fork.strip()
    code, default = git(root, "symbolic-ref", "-q", "refs/remotes/origin/HEAD")
    candidates = ([default.strip()] if code == 0 else []) + list(BASES)
    for candidate in candidates:
        if git(root, "rev-parse", "--verify", "-q", candidate + "^{commit}")[0] == 0:
            code, fork = git(root, "merge-base", "HEAD", candidate)
            return fork.strip() if code == 0 else None
    return None


def open_records(root, wanted_base):
    """Open records, the base commit (or None), and all changed paths."""
    names = set()
    for args in (("diff", "--name-only", "HEAD"), ("ls-files", "--others", "--exclude-standard")):
        code, out = git(root, *args)
        if code == 0:
            names.update(out.splitlines())
    fork = base_commit(root, wanted_base)
    if fork:
        code, out = git(root, "diff", "--name-only", fork, "HEAD")
        if code == 0:
            names.update(out.splitlines())
    records = sorted(name for name in names
                     if name.endswith(".md") and "change-records" in name.split("/")
                     and os.path.isfile(os.path.join(root, name)))
    return records, fork, names


def problem_digest(message):
    """What identifies the problems: their list lines, not the headings around them."""
    lines = [line.strip() for line in message.splitlines() if line.strip().startswith("- ")]
    return hashlib.sha256("\n".join(lines or [message]).encode("utf-8")).hexdigest()


def fallback_state(root):
    """A repository-specific guard when its git folder is read-only."""
    key = hashlib.sha256(os.path.realpath(root).encode("utf-8")).hexdigest()
    return os.path.join(tempfile.gettempdir(), STATE_NAME + "-" + key)


def times_seen(state, digest, session=None):
    """Count consecutive problems in this session; None means storage failed."""
    count = 1
    try:
        with open(state, encoding="utf-8") as handle:
            previous = json.load(handle)
        if previous.get("digest") == digest and previous.get("session") == session:
            count = int(previous["count"]) + 1
    except (OSError, TypeError, ValueError, KeyError, AttributeError):
        pass
    try:
        with open(state, "w", encoding="utf-8") as handle:
            json.dump({"digest": digest, "count": count, "session": session}, handle)
    except (OSError, TypeError):
        return None
    return count


def forget(state):
    try:
        os.remove(state)
    except (OSError, TypeError):
        pass


def before_stop(root, args, payload):
    if not os.path.isfile(os.path.join(HERE, "finish_change.py")):
        raise GateError("finish_change.py is missing next to hook_gate.py; copy the scripts with scaffold_docs.py --hooks")
    sys.path.insert(0, HERE)
    import finish_change     # noqa: E402  (a script of the same folder)
    records, fork, changed = open_records(root, args.base)
    detail = " ".join(records) + ("; no base known" if fork is None else "")
    state = git_path(root, STATE_NAME)
    fallback = fallback_state(root)
    docs_folder = os.path.realpath(os.path.join(root, args.docs))
    scripts_folder = os.path.realpath(os.path.join(root, "tools", "specs"))
    implementation = any(all(os.path.commonpath([os.path.realpath(os.path.join(root, name)), folder]) != folder
                             for folder in (docs_folder, scripts_folder)) for name in changed)
    if not implementation:
        forget(state)
        forget(fallback)
        return PASS, "", detail + ("; waiting for implementation" if records else "")
    since = ["--base", fork] if fork else []
    reports, unfinished = [], False
    for rel in records:
        named = finish_change.record_use_cases(os.path.join(root, rel))
        use_cases = sorted(named) or sorted(set(UC_ID.findall(os.path.basename(rel))))
        if not use_cases:
            reports.append("%s names no use case; the finish check cannot run for it" % rel)
        for uc in use_cases:
            code, out, err = run_script(root, "finish_change.py", uc, "--docs", args.docs, "--record", rel, *since)
            if code == 1:
                unfinished = True
                reports.append("%s, change record %s:\n%s" % (uc, rel, out))
            elif code != 0:
                reports.append("%s, change record %s: the finish check could not run: %s" % (uc, rel, err or out))
    if not unfinished:
        forget(state)
        forget(fallback)
        if reports:
            return WARN, cut("\n\n".join(reports)), detail
        return PASS, "", detail
    message = "\n\n".join(reports)
    session = (payload.get("session_id") or payload.get("conversationId")) if isinstance(payload, dict) else None
    count = times_seen(state, problem_digest(message), session)
    if count is None:
        count = times_seen(fallback, problem_digest(message), session)
    else:
        forget(fallback)
    if count is None:
        return WARN, cut("the loop guard cannot store its state; not blocking\n\n" + message), detail
    if count > REPEATS_BEFORE_GIVING_UP:
        return WARN, cut("The change is still not finished and the same problems came back. "
                         "Stop and report them to the person:\n\n" + message), detail
    return ACT, cut("The change is not finished. Fix these problems before you stop, "
                    "or say which one cannot be fixed and why:\n\n" + message), detail


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


HANDLERS = {"session-start": session_start, "after-edit": after_edit, "before-stop": before_stop}


def main(argv):
    parser = argparse.ArgumentParser(description="One entry point for the agent hooks.")
    parser.add_argument("mode", choices=MODES)
    parser.add_argument("paths", nargs="*", help="after-edit: the edited files, besides those in the tool's JSON")
    parser.add_argument("--docs", help="the specification folder (default: the one the rules block records, else docs)")
    parser.add_argument("--base", help="before-stop: the branch a change starts from")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return PASS if exc.code == 0 else FAILED      # argparse's usage code is 2, which means "act" here
    payload = read_stdin()
    root = None
    try:
        root = repo_root(os.getcwd())
        args.docs = args.docs or docs_folder(root)
        sys.path.insert(0, HERE)
        try:
            import spec_model as model
        except ImportError:
            raise GateError("spec_model.py is missing next to hook_gate.py; copy the scripts with scaffold_docs.py --hooks")
        warning = io.StringIO()
        stop = model.stop_if_old(model.Docs(os.path.join(root, args.docs)), stream=warning)
        if stop:
            verdict, text, detail = WARN, warning.getvalue().rstrip(), "OLD_FORMAT" if stop == model.OLD_FORMAT_EXIT else "UNREADABLE"
        else:
            verdict, text, detail = HANDLERS[args.mode](root, args, payload)
    except GateError as exc:
        verdict, text, detail = FAILED, "hook_gate: %s" % exc, ""
    except Exception as exc:     # a gate must never block by accident
        verdict, text, detail = FAILED, "hook_gate: unexpected error: %s: %s" % (type(exc).__name__, exc), ""
    if text:
        print(text)
        if verdict == FAILED:
            print(text, file=sys.stderr)
    if root:
        log(root, args.mode, verdict, detail)
    return verdict


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
