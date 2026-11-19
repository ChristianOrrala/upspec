#!/usr/bin/env python3
"""Read hook events and render the gate's result for one named agent tool.

The gate keeps results 0 pass, 1 warn, 2 ask and 3 could not run. Profiles
translate those results without running a check or writing the full report.
Only the end of a turn asks: there each profile delivers the questions for the
person by continuing the agent's turn once. At every other moment a result 2 is
rendered as a warning, so no moment blocks or keeps the agent working.
Requires Python 3.9+, standard library only.
"""
import json
import re
from typing import NamedTuple, Optional

# The release these copies belong to; the gate rejects siblings of another release.
UPSPEC_VERSION = "2.1.1"

# Explicit names prevent guessing the calling tool from an unreliable environment.
PROFILES = ("raw", "claude", "codex", "kiro")
AUTO = "auto"


def resolve_profile(name, environ=None):
    """--emit auto: codex when the environment has PLUGIN_ROOT (Codex sets it), else claude."""
    if name != AUTO:
        return name
    import os
    return "codex" if (os.environ if environ is None else environ).get("PLUGIN_ROOT") else "claude"


# The four moments share one gate and differ only in the tool's output contract.
MOMENTS = ("session-start", "after-edit", "before-stop", "turn-start")
# Caps apply to message text, before JSON encoding and its envelope.
CAPS = {
    # Under Claude Code's 10,000-character cap, including for hand-written adapters.
    "raw": 9000,
    # Under Claude Code's 10,000-character cap.
    "claude": 9000,
    # Paths tokenize densely; Codex shows about 2,500 tokens.
    "codex": 6000,
    # Kiro cuts its Stop reason at 4,000 characters.
    "kiro": 3900,
}
# Research 12's delivery contracts, corrected by the proof runs of 2026-10-21 (trial 04); raw depends on an adapter.
CAPABILITIES = {
    "raw": {"turn_start": "nobody", "after_edit": "nobody", "stop_keeps_working": False, "warning_channel": False, "proven_on": ""},
    "claude": {"turn_start": "agent", "after_edit": "agent", "stop_keeps_working": True, "warning_channel": True,
               "proven_on": "Claude Code 2.1.307"},
    "codex": {"turn_start": "agent", "after_edit": "agent", "stop_keeps_working": True, "warning_channel": True,
              "proven_on": "Codex 0.159.2"},
    "kiro": {"turn_start": "agent", "after_edit": "person", "stop_keeps_working": True, "warning_channel": True,
             "proven_on": "Kiro CLI 2.33.1 (V3 engine)"},
}
# Preserve the gate's edited-file keys and add Antigravity's AbsolutePath.
PATH_KEY = re.compile(r"(^|_)(file_?path|path|paths|target_?file|filename|absolute_?path)$", re.IGNORECASE)
# Session metadata must never be mistaken for edited paths, even inside nested objects.
SESSION_KEY = re.compile(r"transcript|cwd|dir|workspace", re.IGNORECASE)
# apply_patch names additions, edits and rename destinations on these lines.
PATCH_FILE = re.compile(r"^\*\*\* (?:(?:Update|Add) File|Move to): (.+)$", re.MULTILINE)
# Tools use these spellings; the first usable id in this order identifies a session.
SESSION_KEYS = ("session_id", "sessionId", "conversationId", "conversation_id")
# The gate's root fallback uses the first usable workspace path after cwd.
WORKSPACE_KEYS = ("workspacePaths", "workspace_roots")
# The gate stores the uncut message here; this notice itself counts toward the cap.
CUT_NOTICE = "\n... cut here; full report: up-hooks-report.txt in the git folder"


class Event(NamedTuple):
    session_id: Optional[str]
    cwd: Optional[str]
    workspace: Optional[str]
    paths: list[str]
    stop_active: bool


class Output(NamedTuple):
    stdout: str
    stderr: str
    code: int


def _paths(node):
    """Keep the gate's recursive path and patch rules, ignoring session metadata."""
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
                found.extend(_paths(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_paths(item))
    elif isinstance(node, str):
        found.extend(name.strip() for name in PATCH_FILE.findall(node))
    return found


def read_event(payload) -> Event:
    """Normalize a decoded tool payload; missing or mistyped metadata stays empty."""
    try:
        edited = _paths(payload)
    except RecursionError:
        return Event(None, None, None, [], False)
    fields = payload if isinstance(payload, dict) else {}
    session = next((fields[key] for key in SESSION_KEYS
                    if isinstance(fields.get(key), str) and fields[key]), None)
    cwd = fields.get("cwd")
    cwd = cwd if isinstance(cwd, str) and cwd else None
    workspace = None
    for key in WORKSPACE_KEYS:
        paths = fields.get(key)
        if isinstance(paths, list):
            workspace = next((path for path in paths if isinstance(path, str) and path), None)
            if workspace:
                break
    return Event(session, cwd, workspace, edited, fields.get("stop_hook_active") is True)


def _cut(text, cap, report_saved=True):
    if len(text) <= cap:
        return text
    notice = CUT_NOTICE if report_saved else "\n... cut here; the full report could not be saved"
    return text[:cap - len(notice)] + notice


def _json(value):
    return Output(json.dumps(value) + "\n", "", 0)


def _validate(profile, moment):
    if profile not in PROFILES:
        raise ValueError("unknown hook profile: %s" % profile)
    if moment not in MOMENTS:
        raise ValueError("unknown hook moment: %s" % moment)


def message(profile: str, moment: str, result: int, text: str, *, cap=None, report_saved=True) -> str:
    """Compose the complete message shared by rendering and report storage."""
    _validate(profile, moment)
    if result not in (0, 1, 2, 3):
        raise ValueError("unknown hook result: %s" % result)
    # Files decoded with surrogateescape can carry code points strict JSON readers reject.
    text = text.encode("utf-8", "replace").decode("utf-8")
    return _cut(text, cap, report_saved) if cap is not None else text


def message_cap(profile, moment):
    # Kiro cuts prompt context at 3,000; leave 100 characters for its final newline and wrapper.
    return 2900 if profile == "kiro" and moment == "turn-start" else CAPS[profile]


def render(profile: str, moment: str, result: int, text: str, *, report_saved=True) -> Output:
    """Translate one internal result, cutting only the message, never the JSON."""
    _validate(profile, moment)
    text = message(profile, moment, result, text, cap=message_cap(profile, moment), report_saved=report_saved)
    if result == 2 and moment != "before-stop":
        result = 1                  # only the end of a turn may ask; elsewhere the text is information
    if moment == "turn-start":
        if result != 0 or not text:
            return Output("", "", 0)
        if profile in ("claude", "codex"):
            return _json({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": text}})
        return Output(text + "\n", "", 0)
    printed = text + "\n" if text else ""
    if profile == "raw":
        return Output(printed, printed if result == 3 else "", result)
    if profile in ("claude", "codex"):
        if result == 0:
            if moment == "session-start" and text:
                return _json({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}})
            return Output("", "", 0)
        if result == 2:
            # The one question at the end of a turn: the tool continues the agent's turn once, to ask it.
            return _json({"decision": "block", "reason": text})
        if result == 1 and moment == "after-edit":
            # Findings reach the agent as context to the edit, and the person as a warning.
            return _json({"systemMessage": text,
                          "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": text}})
        return _json({"systemMessage": text})
    # Kiro ignores nonzero exits other than 1 at Stop; 1 would accidentally continue it.
    if result == 0:
        return Output(printed if moment == "session-start" else "", "", 0)
    if result == 2:
        return _json({"decision": "block", "reason": text})
    return Output("", printed, 3)
