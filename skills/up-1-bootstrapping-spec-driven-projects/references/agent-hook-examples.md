# Agent hook examples

Examples, not rules: how the three hooks of agent-hooks.md were wired into
four tools. Each one names the version it was checked against. Read the
tool's own documentation before copying one; hook formats change.
When the base is not found automatically, add `--base <branch>` to the
before-stop command or set `UP_BASE`.

## Contents

- Claude Code
- Codex CLI
- Antigravity CLI
- Kiro (CLI V3 and IDE 1.x)
- Other tools

Every example changes to the repository root and runs the gate only when the
copy that `scaffold_docs.py --hooks` made in `tools/specs/` exists.

## Claude Code

Example, checked against Claude Code 2.1.285; the desktop app and the IDE
extensions read the same settings. All three hooks were seen firing.

File: `.claude/settings.json`, committed. Claude Code reads exit 2 with
standard error as "block", and for its Stop event as "keep working"; plain
standard output of a SessionStart hook becomes context. No adapter is needed:

```json
{
  "hooks": {
    "SessionStart": [{"matcher": "startup|resume", "hooks": [{"type": "command",
      "command": "cd \"$CLAUDE_PROJECT_DIR\" && if [ -f tools/specs/hook_gate.py ]; then python3 tools/specs/hook_gate.py session-start; fi"}]}],
    "PostToolUse": [{"matcher": "Edit|Write", "hooks": [{"type": "command",
      "command": "cd \"$CLAUDE_PROJECT_DIR\" && if [ -f tools/specs/hook_gate.py ]; then python3 tools/specs/hook_gate.py after-edit 1>&2; fi"}]}],
    "Stop": [{"hooks": [{"type": "command",
      "command": "cd \"$CLAUDE_PROJECT_DIR\" && if [ -f tools/specs/hook_gate.py ]; then python3 tools/specs/hook_gate.py before-stop 1>&2; fi"}]}]
  }
}
```

- The agent cannot write `.claude/` without the person's approval.
- A warning (exit 1) reaches the person only.
- Claude Code itself lets the agent stop after eight Stop blocks in a row.

To run the specification check only on use case files, replace the
`PostToolUse` entry with one group per tool, each narrowed with an `if` rule
on the project's own use case folder. A rule for one tool does not cover
another: `Edit(...)` alone misses a new specification created with Write.
Seen firing with Claude Code 2.1.285: an edit and a new file in the use case
folder fired, a file elsewhere did not. Replace `docs/use_cases/` in both
rules with the project's own use case folder.

```json
{
  "hooks": {
    "PostToolUse": [
      {"matcher": "Edit", "hooks": [{"type": "command", "if": "Edit(docs/use_cases/**)",
        "command": "cd \"$CLAUDE_PROJECT_DIR\" && if [ -f tools/specs/hook_gate.py ]; then python3 tools/specs/hook_gate.py after-edit 1>&2; fi"}]},
      {"matcher": "Write", "hooks": [{"type": "command", "if": "Write(docs/use_cases/**)",
        "command": "cd \"$CLAUDE_PROJECT_DIR\" && if [ -f tools/specs/hook_gate.py ]; then python3 tools/specs/hook_gate.py after-edit 1>&2; fi"}]}
    ]
  }
}
```

## Codex CLI

Example, checked against Codex CLI 0.159.2; the desktop app runs the same
hooks. All three hooks were seen firing, through an adapter.

File: `.codex/hooks.json`, committed. Codex runs project hooks only in a
trusted project and only after the person trusts each hook (in `/hooks` or in
the app); a changed hook must be trusted again.

```json
{
  "hooks": {
    "SessionStart": [{"matcher": "^(startup|resume)$", "hooks": [{"type": "command",
      "command": "cd \"$(git rev-parse --show-toplevel)\" && if [ -f .codex/up_hook.py ]; then python3 .codex/up_hook.py session-start; fi"}]}],
    "PostToolUse": [{"matcher": "^(apply_patch|Edit|Write)$", "hooks": [{"type": "command",
      "command": "cd \"$(git rev-parse --show-toplevel)\" && if [ -f .codex/up_hook.py ]; then python3 .codex/up_hook.py after-edit; fi"}]}],
    "Stop": [{"hooks": [{"type": "command",
      "command": "cd \"$(git rev-parse --show-toplevel)\" && if [ -f .codex/up_hook.py ]; then python3 .codex/up_hook.py before-stop; fi"}]}]
  }
}
```

The adapter `.codex/up_hook.py` passes its standard input to
`tools/specs/hook_gate.py` and prints Codex's JSON, exiting 0. When
`tools/specs/hook_gate.py` is missing, the adapter answers as for result 3.

| Gate result | Session start | After an edit | Before the stop |
|---|---|---|---|
| 0 with text | `hookSpecificOutput` with `hookEventName` and `additionalContext` | nothing | nothing |
| 1 or 3 | `systemMessage` | `systemMessage` | `systemMessage` |
| 2 | — | `decision: "block"` with `reason` | `decision: "block"` with `reason`; `systemMessage` instead when the input has `stop_hook_active: true` |

Edits arrive as `apply_patch`; the file names are inside the patch text, and
the gate reads them there.

## Antigravity CLI

Example, checked against Antigravity CLI (`agy`) 1.2.16 with Gemini. All three
hooks were seen firing in the CLI, through an adapter. Whether the desktop
app runs workspace hooks is disputed: prove it there separately.

File: `.agents/hooks.json`, committed; it loads in a trusted folder. Hooks run
in the folder of that file. The file holds named groups:

```json
{
  "up-session-state": {"SessionStart": [{"type": "command",
    "command": "cd \"$(git rev-parse --show-toplevel)\" && if [ -f .agents/up_hook.py ]; then python3 .agents/up_hook.py session-start; fi"}]},
  "up-specification-check": {"PostToolUse": [{"matcher": "write_to_file|replace_file_content|multi_replace_file_content",
    "hooks": [{"type": "command", "command": "cd \"$(git rev-parse --show-toplevel)\" && if [ -f .agents/up_hook.py ]; then python3 .agents/up_hook.py after-edit; fi"}]}]},
  "up-finish-check": {"Stop": [{"type": "command",
    "command": "cd \"$(git rev-parse --show-toplevel)\" && if [ -f .agents/up_hook.py ]; then python3 .agents/up_hook.py before-stop; fi"}]}
}
```

The adapter `.agents/up_hook.py` answers as below; when
`tools/specs/hook_gate.py` is missing, it answers as for result 3:

| Gate result | Session start | After an edit | Before the stop |
|---|---|---|---|
| 0 with text | `{"injectSteps": [{"ephemeralMessage": <text>}]}` | `{}` | `{"decision": "allow"}` |
| 1 or 3 | `{}` (no channel for a warning was found) | `{}` | `{"decision": "allow"}` |
| 2 | — | the text on standard error, exit 2 | `{"decision": "continue", "reason": <text>}` |

The documentation of this version lists no session-start event and no
feedback from a post-edit hook; both worked. Exit codes other than 0 are not
documented.

## Kiro (CLI V3 and IDE 1.x)

Example from the Kiro documentation read 2026-10-03, **not seen firing**:
prove it before relying on it. A user reported hook files ignored by one CLI
V3 release.

File: `.kiro/hooks/up.json`, committed; CLI V3 and IDE 1.x read the same
files. Kiro asks before the agent writes a hook file.

```json
{
  "version": "v1",
  "hooks": [
    {"name": "up-session-state", "trigger": "SessionStart", "enabled": true, "timeout": 60,
     "action": {"type": "command", "command": "cd \"$(git rev-parse --show-toplevel)\" && if [ -f tools/specs/hook_gate.py ]; then python3 tools/specs/hook_gate.py session-start; fi"}},
    {"name": "up-specification-check", "trigger": "PostToolUse", "matcher": "write", "enabled": true, "timeout": 60,
     "action": {"type": "command", "command": "cd \"$(git rev-parse --show-toplevel)\" && if [ -f tools/specs/hook_gate.py ]; then python3 tools/specs/hook_gate.py after-edit 1>&2; fi"}},
    {"name": "up-finish-check", "trigger": "Stop", "enabled": true, "timeout": 120,
     "action": {"type": "command", "command": "cd \"$(git rev-parse --show-toplevel)\" && if [ -f .kiro/up_hook.py ]; then python3 .kiro/up_hook.py before-stop; fi"}}
  ]
}
```

- Session start: standard output of exit 0 becomes context; no adapter.
- After an edit: standard error of exit 2 goes to the agent.
- Before the stop: the adapter `.kiro/up_hook.py` prints
  `{"decision": "block", "reason": <text>}` with exit 0 on gate result 2, and
  nothing otherwise. When `tools/specs/hook_gate.py` is missing, the adapter
  answers as for result 3. Documented for the CLI; not documented for the IDE.
- The older formats (hooks inside an agent file for CLI V2, `.kiro.hook`
  files for IDE 0.x) use other event names: `agentSpawn`, `postToolUse` with
  `fs_write`, `stop`.

With file events, the specification check can be narrowed to the use case
folder; a new specification is a created file, so include both save and create.
Kiro substitutes `{{filePath}}` for file triggers, and the gate takes that path
as an argument. This variant replaces the `PostToolUse` entry, the matcher
must name the project's own use case folder, and, like the rest of the Kiro
example, it has not been seen firing.

```json
{
  "version": "v1",
  "hooks": [
    {
      "name": "up-specification-save-check",
      "trigger": "PostFileSave",
      "matcher": "docs/use_cases/UC-\\d{3}[^/]*\\.md$",
      "enabled": true,
      "timeout": 60,
      "action": {
        "type": "command",
        "command": "cd \"$(git rev-parse --show-toplevel)\" && if [ -f tools/specs/hook_gate.py ]; then python3 tools/specs/hook_gate.py after-edit \"{{filePath}}\" 1>&2; fi"
      }
    },
    {
      "name": "up-specification-create-check",
      "trigger": "PostFileCreate",
      "matcher": "docs/use_cases/UC-\\d{3}[^/]*\\.md$",
      "enabled": true,
      "timeout": 60,
      "action": {
        "type": "command",
        "command": "cd \"$(git rev-parse --show-toplevel)\" && if [ -f tools/specs/hook_gate.py ]; then python3 tools/specs/hook_gate.py after-edit \"{{filePath}}\" 1>&2; fi"
      }
    }
  ]
}
```

## Other tools

Gemini CLI keeps hooks in `.gemini/settings.json`: `SessionStart`, `AfterTool`
filtered on `write_file|replace`, and `AfterAgent` answering
`{"decision": "deny", "reason": ...}` to keep the agent working; timeouts are
in milliseconds. Not checked here. For any tool: find its three events in its
documentation, follow the wiring rules, prove each hook.
