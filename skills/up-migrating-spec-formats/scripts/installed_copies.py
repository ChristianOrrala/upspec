"""Classify installed copies and record package baselines for setup and migration.

Imported from the plugin, never installed into the project. Python 3.9+,
standard library only. Classification reads files without recording baselines.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile

# Identify the release whose installed copies this module helps update.
# Keep the installation record beside the scripts it describes.
UPSPEC_VERSION = "1.1.0"
BUNDLE_NAME = "upspec-installed.json"
# Match setup's hook copies without importing a module absent from the migration skill.
HOOK_SET = ("hook_gate.py", "workflow_state.py", "validate_use_case.py", "finish_change.py", "scope_audit.py",
            "uc_change_list.py", "unrecorded_changes.py", "spec_model.py", "use_case_map.py", "change_view.py", "hook_profiles.py")
# Match setup's pipeline copies; tests pin both tuples to setup's installation lists.
CHECK_SET = ("spec_model.py", "validate_use_case.py", "spec_lint.py", "use_case_map.py", "spec_first_guard.py")


def fingerprint(data):
    """Return the SHA-256 of bytes, or None for an absent copy, as migration does."""
    return hashlib.sha256(data).hexdigest() if data is not None else None


def script_version(path):
    """Read a literal release identifier without importing or running the script."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    match = re.search(r'^UPSPEC_VERSION = "(\d+\.\d+\.\d+)"$', text, re.M)
    return match.group(1) if match else None


def read_bundle(folder):
    """Read an installation record; a missing or unreadable record gives no baseline."""
    try:
        bundle = json.loads((Path(folder) / BUNDLE_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return {}
    return bundle if isinstance(bundle, dict) else {}


def write_bundle(folder, bundle):
    """Replace the record atomically, preserving all supplied fields, including wiring."""
    target = Path(folder) / BUNDLE_NAME
    try:
        mode = stat.S_IMODE(target.stat().st_mode)
    except FileNotFoundError:
        mask = os.umask(0)
        os.umask(mask)
        # New records use normal file creation permissions under the caller's umask.
        mode = 0o666 & ~mask
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=folder,
                                         prefix=BUNDLE_NAME + ".", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(bundle, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fchmod(handle.fileno(), mode)
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def classify(path, current, known, bundle):
    """Return missing, current, kept, untouched or changed, without writing anything."""
    path = Path(path)
    try:
        installed = path.read_bytes()
    except FileNotFoundError:
        return "missing"
    if installed == current:
        return "current"

    scripts = bundle.get("scripts", {})
    if not isinstance(scripts, dict):
        scripts = {}
    entry = scripts.get(path.name, {})
    if not isinstance(entry, dict):
        entry = {}
    found = fingerprint(installed)
    if entry.get("kept") == found:
        return "kept" if entry.get("baseline") == fingerprint(current) else "changed"
    if entry.get("baseline") == found:
        return "untouched"
    if "baseline" not in entry and found in known.get(path.name, ()):
        return "untouched"
    return "changed"


def sets_installed(folder):
    """Identify installed hook and check sets by their entry points."""
    folder = Path(folder)
    installed = set()
    if (folder / "hook_gate.py").is_file():
        installed.add("hook")
    if (folder / "spec_first_guard.py").is_file():
        installed.add("check")
    return installed
