"""Resolve the base of a change from project settings and local git history.

The finish check, scope audit and hook gate share this reader. All git calls
are read-only; no remote is contacted. Requires Python 3.9+, standard library only.
"""
from __future__ import annotations

import os
import re
from typing import NamedTuple

import spec_model

# The release these shared copies belong to, checked alongside installed scripts.
UPSPEC_VERSION = "1.2.0"

# The integration branches the common hosts and branching models use.
INTEGRATION_NAMES = ("main", "master", "dev", "develop")

# Root tracking documents describe the work rather than implementing behavior.
A_FILES = ("ACTIVE.md", "ABILITIES.md", "AHEAD.md", "ATLAS.md")

# Sixteen paths at the usual 4 KiB POSIX path limit use about 64 KiB of arguments.
DELETED_BATCH_SIZE = 16


class Base(NamedTuple):
    commit: str | None
    ref: str | None
    source: str


class BaseError(Exception):
    """A named base cannot be resolved; its setting source is in the message."""


def _git(root, *args):
    """Use the shared 60-second git timeout and preserve non-ASCII paths."""
    return spec_model.git(("-c", "core.quotePath=false") + args, cwd=root)


def _short_ref(ref):
    for prefix in ("refs/heads/", "refs/remotes/"):
        if ref.startswith(prefix):
            return ref[len(prefix):]
    return ref


def _best(root, candidates, current, source):
    """Drop the current local branch, then rank by commits missing from each ref."""
    candidates = list(dict.fromkeys(candidates))
    alternatives = [ref for ref in candidates if ref != current]
    fallback = current in candidates and bool(alternatives)
    if alternatives:
        candidates = alternatives
    ranked = []
    for ref in candidates:
        code, count = _git(root, "rev-list", "--count", ref + "..HEAD")
        if code == 0:
            ranked.append((int(count.strip()), ref))
    for _, ref in sorted(ranked, key=lambda item: item[0]):
        code, commit = _git(root, "merge-base", "HEAD", ref)
        if code == 0:
            return Base(commit.strip(), _short_ref(ref), source)
        if source != "auto":
            return Base(None, _short_ref(ref), source)
    if source == "auto" and fallback:
        return _best(root, [current], current, source)
    return Base(None, None, "none")


def _base_refs(root):
    """Read refs and the current branch once for either named or detected bases."""
    code, output = _git(root, "for-each-ref", "--format=%(refname)%00%(symref)")
    refs = dict(line.split("\0", 1) for line in output.splitlines()) if code == 0 else {}
    remotes = sorted({ref[len("refs/remotes/"):].split("/", 1)[0]
                      for ref in refs if ref.startswith("refs/remotes/")},
                     key=lambda remote: (remote != "origin", remote))
    code, current = _git(root, "symbolic-ref", "-q", "HEAD")
    current = current.strip() if code == 0 else None
    return refs, remotes, current


def detect_base(root: str) -> Base:
    """Select an integration base from git history alone, without project settings."""
    refs, remotes, current = _base_refs(root)
    candidates = []
    for remote in remotes:
        default = refs.get("refs/remotes/" + remote + "/HEAD")
        if default in refs:
            candidates.append(default)
        candidates.extend("refs/remotes/" + remote + "/" + branch for branch in INTEGRATION_NAMES
                          if "refs/remotes/" + remote + "/" + branch in refs)
    candidates.extend("refs/heads/" + branch for branch in INTEGRATION_NAMES
                      if "refs/heads/" + branch in refs)
    return _best(root, candidates, current, "auto")


def resolve_base(root: str, wanted: str | None = None) -> Base:
    """Resolve --base, UP_BASE, git config up.base, the rules block, then detection.

    Bare branch names consider local and remote copies. A qualified remote ref
    or commit is used directly. Missing named settings fail instead of silently
    selecting an unrelated base. Without candidates, the base is unknown.
    """
    source = "--base"
    name = wanted
    if not name:
        source, name = "UP_BASE", os.environ.get("UP_BASE")
    if not name:
        source = "git config up.base"
        code, configured = _git(root, "config", "--get", "up.base")
        name = configured.strip() if code == 0 else None
    if not name:
        source, name = "rules block", spec_model.integration_branch(root)

    if not name:
        return detect_base(root)
    refs, remotes, current = _base_refs(root)

    branch = name[len("refs/heads/"):] if name.startswith("refs/heads/") else name
    qualified = name.startswith("refs/remotes/") or any(name.startswith(remote + "/")
                                                             for remote in remotes)
    candidates = [] if qualified else [
        ref for ref in ["refs/heads/" + branch] +
        ["refs/remotes/" + remote + "/" + branch for remote in remotes] if ref in refs]
    if candidates:
        result = _best(root, candidates, current, source)
    else:
        ref = "refs/remotes/" + name if qualified and not name.startswith("refs/") else name
        code, commit = _git(root, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}")
        if code:
            raise BaseError("%s names '%s', which exists neither locally nor on a remote" % (source, name))
        code, fork = _git(root, "merge-base", "HEAD", commit.strip())
        result = Base(fork.strip() if code == 0 else None, name, source)
    if result.commit is None:
        raise BaseError("%s names '%s', but no common base with HEAD can be read" % (source, name))
    return result


class ChangeView:
    """A run's base, changed paths and lazily read working-tree text."""

    def __init__(self, root: str, base: Base, docs_rel: str):
        self.root = os.path.abspath(root)
        self.base = base
        self.docs_rel = docs_rel.replace(os.sep, "/").rstrip("/")
        self.docs = spec_model.Docs(os.path.join(self.root, self.docs_rel))
        self._texts = {}
        self._files = None
        self.changed: dict[str, str] = self._changed()

    def _changed(self):
        changed = {}
        if self.base.commit:
            code, output = _git(self.root, "diff", "--relative", "--name-status", "-z", "-M",
                                self.base.commit, "--", ".")
            if code == 0:
                fields = iter(output.rstrip("\0").split("\0"))
                for status in fields:
                    if not status:
                        continue
                    path = next(fields)
                    if status.startswith(("R", "C")):
                        path = next(fields)
                    changed[path] = status[0] if status[0] in "AMDR" else "M"
        else:
            code, prefix = _git(self.root, "rev-parse", "--show-prefix")
            prefix = prefix.rstrip("\n") if code == 0 else None
            code, output = _git(self.root, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--", ".")
            if code == 0 and prefix is not None:
                fields = iter(output.rstrip("\0").split("\0"))
                for entry in fields:
                    if not entry:
                        continue
                    status, path = entry[:2], entry[3:]
                    if "R" in status or "C" in status:
                        next(fields)
                    if not path.startswith(prefix):
                        continue
                    path = path[len(prefix):]
                    changed[path] = ("A" if status == "??" or "A" in status else
                                     "D" if "D" in status else "R" if "R" in status else "M")
        code, output = _git(self.root, "ls-files", "-z", "--others", "--exclude-standard")
        if code == 0:
            for path in output.split("\0"):
                if path:
                    changed.setdefault(path, "A")
        code, output = _git(self.root, "ls-files", "-z", "--others", "--ignored", "--exclude-standard",
                            "--", self.docs_rel + "/")
        if code == 0:
            for path in output.split("\0"):
                if path.endswith(".md") and self.kind(path) != "change_record":
                    changed.setdefault(path, "A")
        # Running installed checks produces bytecode caches; they never belong to a change.
        return {path: status for path, status in sorted(changed.items())
                if "__pycache__" not in path.split("/")[:-1]}

    def files(self, suffixes=None) -> list[str]:
        """Absolute source paths, including untracked files and excluding ignored ones."""
        if self._files is None:
            self._files = list(spec_model.iter_source_files(self.root))
        return [path for path in self._files if not suffixes or path.endswith(tuple(suffixes))]

    def text(self, path) -> str | None:
        path = os.path.abspath(os.path.join(self.root, path))
        if path not in self._texts:
            try:
                with open(path, encoding="utf-8") as handle:
                    text = handle.read()
                self._texts[path] = text if "\0" not in text else None
            except (OSError, UnicodeDecodeError):
                self._texts[path] = None
        return self._texts[path]

    def markers(self, ids) -> set[str]:
        ids = set(ids)
        if not ids:
            return set()
        patterns = [pattern for uc_id in ids for pattern in spec_model._marker_patterns(uc_id)]
        return {path for path in spec_model._marker_paths(self.root, ids)
                if self.text(path) is not None and any(pattern.search(self.text(path)) for pattern in patterns)}

    def _in_docs(self, path):
        return path.startswith(self.docs_rel + "/")

    def references(self, name) -> list[str]:
        return self.references_many({name})[name]

    def references_many(self, names) -> dict[str, list[str]]:
        """Find non-test source references with one grep for all distinct names."""
        found = {name: [] for name in sorted(set(names))}
        if not found:
            return found
        args = ["grep", "-z", "-l", "-F", "-w", "--untracked"]
        for name in found:
            args.extend(("-e", name))
        code, output = _git(self.root, *args, "--")
        if code == 1:
            return found
        paths = ([os.path.join(self.root, path) for path in output.split("\0")
                  if path and spec_model.source_path(path)] if code == 0 else self.files())
        patterns = {name: re.compile(r"(?<!\w)%s(?!\w)" % re.escape(name)) for name in found}
        for path in sorted(paths):
            relative = os.path.relpath(path, self.root).replace(os.sep, "/")
            if self._in_docs(relative) or spec_model.is_test_path(relative):
                continue
            text = self.text(path)
            if text is not None:
                for name, pattern in patterns.items():
                    if pattern.search(text):
                        found[name].append(path)
        return found

    def deleted_carrying(self, ids) -> set[str]:
        deleted = [path for path, status in self.changed.items() if status == "D"]
        ids = sorted(set(ids))
        if not self.base.commit or not deleted or not ids:
            return set()
        patterns = [pattern for uc_id in ids for pattern in spec_model._marker_patterns(uc_id)]
        args = ["--literal-pathspecs", "grep", "-z", "-l", "-F"]
        for uc_id in ids:
            args.extend(("-e", uc_id, "-e", spec_model.compact_id(uc_id)))
        found = set()
        for start in range(0, len(deleted), DELETED_BATCH_SIZE):
            batch = deleted[start:start + DELETED_BATCH_SIZE]
            code, output = _git(self.root, *args, self.base.commit, "--", *batch)
            if code == 1:
                continue
            if code != 0:
                return set()
            for name in output.split("\0"):
                if not name:
                    continue
                path = name[len(self.base.commit) + 1:]
                # Git's binary check does not reject every undecodable text file.
                code, text = _git(self.root, "show", self.base.commit + ":./" + path)
                try:
                    text = text.encode("utf-8", errors="surrogateescape").decode("utf-8")
                except UnicodeDecodeError:
                    continue
                if code == 0 and "\0" not in text and any(pattern.search(text) for pattern in patterns):
                    found.add(os.path.join(self.root, path))
        return found

    def changed_specs(self) -> list[str]:
        return [path for path, status in self.changed.items()
                if status != "D" and self.kind(path) == "use_case"]

    def kind(self, path: str) -> str | None:
        """Classify a repository-relative path with the shared docs rules."""
        return self.docs.kind(os.path.join(self.root, path))

    def work_files(self) -> set[str]:
        guideline, _ = spec_model._rules_block_text(self.root)
        paths = set(self.changed)
        for folder in (self.docs_rel, "tools/specs"):
            for directory, _, names in os.walk(os.path.join(self.root, folder)):
                paths.update(os.path.relpath(os.path.join(directory, name), self.root).replace(os.sep, "/")
                             for name in names)
        work = {path for path in paths if self._in_docs(path) or path.startswith("tools/specs/")}
        work.update(name for name in A_FILES if os.path.isfile(os.path.join(self.root, name)))
        if guideline:
            work.add(guideline)
        return work

    def is_implementation(self) -> bool:
        return bool(set(self.changed) - self.work_files())


def build(root: str, wanted_base: str | None = None, docs_rel: str | None = None) -> ChangeView:
    """Build an independent view; invalid explicit bases propagate as BaseError."""
    root = os.path.abspath(root)
    return ChangeView(root, resolve_base(root, wanted_base), docs_rel or spec_model.docs_default(root))


def view_for(root: str, base: str, docs_rel: str) -> ChangeView:
    """Use the requested base, allowing an unborn HEAD to show uncommitted files."""
    if base == "HEAD":
        code, commit = _git(root, "rev-parse", "--verify", "HEAD")
        resolved = Base(commit.strip(), "HEAD", "--base") if code == 0 else Base(None, None, "none")
        return ChangeView(root, resolved, docs_rel)
    return build(root, base, docs_rel)
