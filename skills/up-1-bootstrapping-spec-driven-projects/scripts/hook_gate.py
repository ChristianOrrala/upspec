#!/usr/bin/env python3
"""One entry point for the agent hooks, whatever tool calls it.

    hook_gate.py session-start [--docs DIR]
        the state of the specifications, as context for a new session
    hook_gate.py after-edit [PATH ...] [--docs DIR]
        the validator on every use case specification among the edited files
    hook_gate.py before-stop [--docs DIR] [--base REF]
        validate changed specifications, then finish open implementation records

Every moment accepts --emit raw|claude|codex|antigravity|kiro (default: raw).
A profile renders the internal result for the calling tool.

Edited paths come from the arguments and from the JSON the tool writes to
stdin: every string under a key that names a file path, and the file names on
the "*** Update File:", "*** Add File:" and "*** Move to:" lines of a patch body. Paths that
belong to the session (transcript, working directory, workspace) are ignored,
and a relative path is read from the session's directory when the JSON names
one. A change record is never taken for a specification, even when its name
starts with a use case's identifier.

A change record is open when it is added or changed and not committed, or
changed on the current branch since it left the base branch (--base, else the
environment variable UP_BASE, git config up.base, the rules block, then detected
integration branches).
Once the change touches files outside the specification folder, tools/specs/,
the rules-block guideline and root A-files,
the finish check runs against the commit where the branch left its base.
During triage, specification writing and review it waits for implementation.

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
import os
import re
import subprocess
import sys
import threading
import tempfile

# the release these copies belong to; hook_gate.py refuses siblings of another release
UPSPEC_VERSION = "1.1.0"

sys.dont_write_bytecode = True   # a __pycache__ folder in tools/specs/ would be an unexplained file in every change

HERE = os.path.dirname(os.path.abspath(__file__))
UC_ID = re.compile(r"\bUC-\d{3}\b")
SPEC_NAME = re.compile(r"^UC-\d{3}\b.*\.md$")
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
MODES = ("session-start", "after-edit", "before-stop")
# Match the installed hook bundle without importing possibly incompatible siblings.
BUNDLE_SCRIPTS = ("workflow_state.py", "validate_use_case.py", "finish_change.py", "scope_audit.py",
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


def could_not_run(name, exc):
    return Verdict(FAILED, "%s could not run: %s: %s" % (name, type(exc).__name__, exc), "")


def session_start(root, args, event):
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
    if len(lines) > MAX_CONTEXT_LINES:
        next_step = next((i for i, line in enumerate(lines) if line.startswith("Next step:")), len(lines))
        tail = lines[next_step:]
        head_count = max(0, MAX_CONTEXT_LINES - len(tail))
        head_count = min(head_count, next_step)
        rest = next_step - head_count
        lines = lines[:head_count] + ["... %d more lines: run workflow_state.py for the full state" % rest] + tail
    return Verdict(PASS, "Specification state of this repository:\n" + "\n".join(lines), "")


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
            checked = validate_use_case.validate_files(paths, docs_dir=docs, report=report)
        if isinstance(checked, int):
            if checked == spec_model.OLD_FORMAT_EXIT:
                return Verdict(WARN, notice.getvalue().strip(), "OLD_FORMAT")
            return could_not_run("validate_use_case.py", GateError("unexpected result %s" % checked))
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
                  if name.endswith(".md") and "change-records" in name.split("/")
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


def finish_checks(view, args, event, records, detail):
    """Collect each open record's finish problems, containing failures per record."""
    root = view.root
    reports, unfinished = [], False
    for rel in records:
        try:
            import finish_change
            named = finish_change.record_use_cases(os.path.join(root, rel))
            use_cases = sorted(named) or sorted(set(UC_ID.findall(os.path.basename(rel))))
        except BaseException as exc:
            reports.append("change record %s: the finish check could not run: %s: %s" %
                           (rel, type(exc).__name__, exc))
            continue
        if not use_cases:
            reports.append("%s names no use case; the finish check cannot run for it" % rel)
        for uc in use_cases:
            try:
                check_args = argparse.Namespace(use_case=uc, docs=args.docs, record=rel,
                                                base=view.base.ref or "HEAD", format="text", code=None, tests=None)
                code, out = finish_change.finish_report(check_args, view=view)
                if code == 1:
                    unfinished = True
                    reports.append("%s, change record %s:\n%s" % (uc, rel, out.rstrip()))
                elif code != 0:
                    reports.append("%s, change record %s: the finish check could not run: %s" % (uc, rel, out.rstrip()))
            except BaseException as exc:
                reports.append("%s, change record %s: the finish check could not run: %s: %s" %
                               (uc, rel, type(exc).__name__, exc))
    return Verdict(ACT if unfinished else WARN if reports else PASS, "\n\n".join(reports), detail)


def before_stop(view, args, event) -> Verdict:
    implementation = view.is_implementation()
    specs = view.changed_specs()
    validated = validation(specs, args.docs, ACT if implementation else WARN,
                           "The changed specifications have findings; fix them before going on:")
    records = open_records(view)
    detail = " ".join(records)
    if implementation and records:
        finished = finish_checks(view, args, event, records, detail)
    else:
        finished = Verdict(PASS, "", detail + ("; waiting for implementation" if records else ""))
    results = (validated.result, finished.result)
    combined = Verdict(ACT if ACT in results else max(results),
                       "\n\n".join(text for text in (validated.text, finished.text) if text),
                       "; ".join(part for part in (validated.detail, finished.detail) if part))
    state, fallback = git_path(view.root, STATE_NAME), fallback_state(view.root)
    if combined.result in (PASS, WARN):
        guard_reset(state)
        guard_reset(fallback)
    if combined.result != ACT:
        return combined
    ids = sorted(set(problem_ids(validated.text)) | set(problem_ids(finished.text)))
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
                                 text="The change is still not finished and the same problems came back.\n\n" + combined.text)
    if outcome == "quiet":
        return combined._replace(result=WARN)
    return combined._replace(text="The change is not finished. Fix these problems before you stop, "
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
        event = hook_profiles.read_event(read_stdin())
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
        stop = model.stop_if_old(model.Docs(os.path.join(root, args.docs)), stream=warning)
        if stop:
            verdict = Verdict(WARN, warning.getvalue().rstrip(),
                              "OLD_FORMAT" if stop == model.OLD_FORMAT_EXIT else "UNREADABLE")
        elif args.mode == "before-stop":
            import change_view
            docs_rel = os.path.relpath(os.path.join(root, args.docs), root).replace(os.sep, "/")
            view = change_view.view_for(root, args.base, docs_rel)
            verdict = before_stop(view, args, event)
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
    report_saved = False
    if root:
        base_detail = ("base %s (%s)" % (view.base.ref, view.base.source)
                       if view is not None and view.base.ref else "base none")
        detail = base_detail + ("; " + verdict.detail if verdict.detail else "")
        full_message = hook_profiles.message(profile, args.mode, verdict.result, verdict.text, verdict.give_up)
        if len(full_message) > hook_profiles.CAPS[profile]:
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
