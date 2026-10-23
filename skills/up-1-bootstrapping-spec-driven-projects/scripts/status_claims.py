#!/usr/bin/env python3
"""Check lifecycle claims and validate changed use cases over a git range.

The range selects claims; the resolved integration base selects their evidence.
Exit 0 clean, 1 problems, 2 usage or unknown ref, 5 old specification formats.
With --pre-push, read git ref lines and return 1 only for problems; unavailable
checks pass with a notice. Requires Python 3.9+, standard library only. Reads only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import NamedTuple, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import change_view
    import finish_change
    import spec_model as model
    import validate_use_case
except Exception as exc:
    if __name__ == "__main__" and "--pre-push" in sys.argv:
        print("Status claims: push not checked (cannot load the check: %s)." % exc)
        sys.exit(0)
    raise

# Installed siblings must belong to the same release as the hook gate.
UPSPEC_VERSION = "1.2.0"


class Claim(NamedTuple):
    uc: str
    path: str
    before: Optional[str]
    after: str


def statuses(root: str, docs_rel: str, ref: Optional[str] = None) -> dict[str, tuple[str, str]]:
    """Use case id -> (repository-relative path, Status), at a ref or on disk."""
    root = os.path.abspath(root)
    docs = model.Docs(os.path.join(root, docs_rel))
    if ref is None:
        paths = [os.path.relpath(os.path.join(directory, name), root).replace(os.sep, "/")
                 for directory, _, names in os.walk(docs.root) for name in names
                 if docs.kind(os.path.join(directory, name)) == "use_case"]
    else:
        code, commit = model.git(["rev-parse", "--verify", "--end-of-options", ref + "^{commit}"], cwd=root)
        if code:
            return {}
        ref = commit.strip()
        code, listing = model.git(["ls-tree", "-r", "--name-only", "-z", ref, "--", docs_rel.rstrip("/") + "/"], cwd=root)
        if code:
            return {}
        paths = [path for path in listing.split("\0") if path and
                 docs.kind(os.path.join(root, path)) == "use_case"]
    result = {}
    for path in sorted(paths):
        if ref is None:
            try:
                lines = model.read_lines(os.path.join(root, path))
            except (OSError, UnicodeDecodeError):
                continue
        else:
            code, text = model.git(["show", ref + ":" + path], cwd=root)
            if code:
                continue
            lines = text.splitlines()
        uc = model.parse_use_case_lines(lines, path)
        identifier = uc.field("Use Case ID").strip()
        key = identifier if re.fullmatch(r"UC-\d{3}", identifier) else path
        result[key] = (path, uc.status)
    return result


def find_claims(before: dict, after: dict, own: Optional[set[str]] = None) -> list[Claim]:
    """Lifecycle raises to Implemented or higher, keyed by id so renames are moves."""
    claims = []
    for uc, (path, status) in sorted(after.items()):
        previous = before.get(uc, (None, None))[1]
        rank = model.STATUS_RANK.get(status, -1)
        if (rank >= model.STATUS_RANK["Implemented"] and
                rank > model.STATUS_RANK.get(previous, -1) and (own is None or path in own)):
            claims.append(Claim(uc, path, previous, status))
    return claims


def claim_problems(view, claim: Claim, docs_rel: str, spill: Optional[set[str]],
                   code: Optional[str] = None, tests: Optional[str] = None) -> tuple[list[str], list[str]]:
    """Check a claim through the finish check; Tested and Done cover every unit."""
    args = argparse.Namespace(use_case=claim.uc, docs=os.path.join(view.root, docs_rel),
                              record=None, base=view.base.commit, format="json", claim=True,
                              spill=spill, code=code, tests=tests,
                              spec_path=os.path.join(view.root, claim.path))
    exit_code, text = finish_change.finish_report(args, view)
    if exit_code not in (0, 1):
        return [text.strip()], []
    try:
        report = json.loads(text)
    except ValueError:
        return [text.strip()], []
    problems, warnings = report["problems"], report.get("warnings", [])
    if claim.after in ("Tested", "Done"):
        uc = model.parse_use_case(os.path.join(view.root, claim.path))
        problems += ["no test of %s names %s" % (claim.uc, unit)
                     for unit in finish_change.untested_units(args, view, uc)]
    return list(dict.fromkeys(problems)), list(dict.fromkeys(warnings))


def _main(argv) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--since", help="revision before the claims (default: resolved integration base)")
    parser.add_argument("--base", help="base for the evidence (default: hook base resolution)")
    parser.add_argument("--docs", help="specification folder (default: rules block, else docs)")
    parser.add_argument("--code", help="implementation folder")
    parser.add_argument("--tests", help="test folder")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    selection.add_argument("--first-push", action="store_true",
                           help="empty baseline for the integration or default branch, or without an integration ref; "
                                "otherwise the fork with the integration branch")
    parser.add_argument("--pre-push", action="store_true", help="read git pre-push refs; block only on problems")
    parser.add_argument("remote", nargs="*", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.remote and not args.pre_push:
        parser.error("remote arguments require --pre-push")
    return pre_push(args) if args.pre_push else check(args)


def main(argv) -> int:
    if "--pre-push" not in argv:
        return _main(argv)
    try:
        return _main(argv)
    except SystemExit as exc:
        return exc.code
    except Exception as exc:
        print("Status claims: push not checked (%s). CI stays authoritative." % exc)
        return 0


def pre_push(args) -> int:
    """Check each pushed HEAD range; missing checks and other refs are advisory."""
    code, top = model.git(["rev-parse", "--show-toplevel"], cwd=os.getcwd())
    if code:
        print("Status claims: push not checked (no git repository).")
        return 0
    root = top.strip()
    docs = os.path.abspath(args.docs or os.path.join(root, model.docs_default(root)))
    code, edits = model.git(["status", "--porcelain", "--untracked-files=all", "--", docs], cwd=root)
    if code == 0 and edits.strip():
        print("Status claims: uncommitted docs edits are included; the answer may differ from CI.")
    code, head = model.git(["rev-parse", "--verify", "HEAD"], cwd=root)
    if code:
        print("Status claims: push not checked (HEAD is unavailable).")
        return 0
    lines = sys.stdin.read().splitlines()
    ranges = []
    if not lines:
        ranges.append((args.since, getattr(args, "first_push", False), None))
    for line in lines:
        parts = line.split()
        if len(parts) != 4:
            print("Status claims: push not checked for a malformed ref line.")
            continue
        local_ref, local_sha, remote_ref, remote_sha = parts
        if local_sha and set(local_sha) == {"0"}:
            continue  # Git's zero object id denotes a deletion, with either hash format.
        if local_sha != head.strip():
            print("Status claims: %s is not HEAD; push not checked for this ref." % local_ref)
            continue
        first = bool(remote_sha) and set(remote_sha) == {"0"}
        ranges.append((None if first else remote_sha, first, remote_ref))
    problems = False
    for since, first, pushed_ref in ranges:
        options = argparse.Namespace(**vars(args))
        options.since = since
        options.first_push = first
        options.pushed_ref = pushed_ref
        try:
            result = check(options)
        except (Exception, SystemExit) as exc:
            print("Status claims: push not checked (%s)." % exc)
            continue
        if result == 1:
            problems = True
        elif result != 0:
            print("Status claims: push not checked (check returned %s); CI stays authoritative." % result)
    return int(problems)


def _first_push_uses_empty_baseline(root, base, pushed_ref):
    """Integration and default refs claim their initial contents; topic refs use their fork."""
    if base.ref is None:
        return True
    refs, remotes, current = change_view._base_refs(root)

    def branch(ref):
        if not ref:
            return None
        if ref.startswith("refs/heads/"):
            return ref[len("refs/heads/"):]
        name = change_view._short_ref(ref)
        for remote in remotes:
            if name.startswith(remote + "/"):
                return name[len(remote) + 1:]
        return name

    # CI exports REF_NAME even with detached HEAD; pre-push supplies the destination ref.
    ci_ref = "refs/heads/" + os.environ["REF_NAME"] if os.environ.get("REF_NAME") else None
    pushed = branch(pushed_ref or ci_ref or current)
    integration = branch(base.ref)
    defaults = {branch(refs.get("refs/remotes/" + remote + "/HEAD")) for remote in remotes}
    if os.environ.get("DEFAULT_BRANCH"):
        defaults.add(os.environ["DEFAULT_BRANCH"])
    defaults.discard(None)
    return pushed is not None and (pushed == integration or pushed in defaults)


def check(args) -> int:
    """The range check shared by the CLI and the advisory pre-push adapter."""
    code, top = model.git(["rev-parse", "--show-toplevel"], cwd=os.getcwd())
    if code:
        print("not a git repository (or git is not installed)", file=sys.stderr)
        return 2
    root = top.strip()
    docs = os.path.abspath(args.docs or os.path.join(root, model.docs_default(root)))
    for folder in (docs, args.code, args.tests):
        if folder and not os.path.isdir(folder):
            print("no such folder: %s" % folder, file=sys.stderr)
            return 2
    docs_rel = os.path.relpath(docs, root).replace(os.sep, "/")
    try:
        view = change_view.view_for(root, args.base, docs_rel)
    except change_view.BaseError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    since = args.since or view.base.commit
    first_push = getattr(args, "first_push", False)
    if first_push:
        empty = _first_push_uses_empty_baseline(root, view.base, getattr(args, "pushed_ref", None))
        since = None if empty else view.base.commit
    if since:
        code, resolved = model.git(["rev-parse", "--verify", "--end-of-options", since + "^{commit}"], cwd=root)
        if code:
            print("unknown revision: %s" % since, file=sys.stderr)
            return 2
        since = resolved.strip()
    stop = model.stop_if_old(model.Docs(docs))
    if stop is not None:
        return stop
    selection = (view if since == view.base.commit else
                 change_view.ChangeView(root, change_view.Base(since, args.since, "--since"), docs_rel))
    before = statuses(root, docs_rel, since) if since else {}
    after = statuses(root, docs_rel)
    claims = find_claims(before, after)
    result = {"claims": [], "problems": [], "warnings": []}
    for claim in claims:
        problems, warnings = claim_problems(view, claim, docs_rel, set(), args.code, args.tests)
        result["claims"].append(dict(claim._asdict(), problems=problems, warnings=warnings))
        label = "%s (%s -> %s): " % (claim.uc, claim.before or "absent", claim.after)
        result["problems"].extend(label + line for line in problems)
        result["warnings"].extend(label + line for line in warnings)
    selected = (sorted(path for path, _ in after.values()) if first_push and since is None
                else selection.changed_specs())
    for path in selected:
        full = os.path.join(root, path)
        uc = model.parse_use_case(full)
        report = validate_use_case.validate_files([full], docs_dir=docs, report=model.Reporter(root))
        if isinstance(report, int):
            return report
        strict = model.STATUS_RANK.get(uc.status, -1) >= model.STATUS_RANK["Reviewed"]
        for finding in report.sorted():
            line = "%(path)s:%(line)d: %(code)s [%(element)s]: %(message)s" % finding
            field = "problems" if strict and finding["severity"] == "ERROR" else "warnings"
            result[field].append(line)
    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        for claim in claims:
            print("%s: %s -> %s" % (claim.uc, claim.before or "absent", claim.after))
        for field, label in (("problems", "problem"), ("warnings", "warning")):
            for line in result[field]:
                print("%s: %s" % (label, line))
        if not result["problems"] and not result["warnings"]:
            print("Status claims: clean")
    return 1 if result["problems"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
