# Agent hook examples

The hook files the plugin ships, and what each tool delivers. Nothing here is
written into a project: the plugin carries the files, and the person turns them
on as `agent-hooks.md` says. Each tool's hooks were seen firing with the real
gate on the version named in its section, on 2026-11-16.

The tools inform and never stop the work. After-edit findings arrive as
context. At the stop, owner decisions are asked once; routine notes go to the
agent once as a list to align or include in its handoff, without a question. In
a session with nobody present the decisions are recorded as later instead of
asked. "Stop keeps the agent working" names the channel both kinds use: one
continuation of the turn to deliver them.

## Contents

- Claude Code
- Codex CLI
- Kiro CLI
- OpenCode
- Antigravity CLI
- Other tools

## Claude Code

File: `hooks/hooks.json` at the plugin's root, loaded when the plugin is
installed. Its four commands run the gate from the plugin's folder:

```text
python3 "${CLAUDE_PLUGIN_ROOT}/skills/up-bootstrapping-spec-driven-projects/scripts/hook_gate.py" <moment> --emit auto
```

The events are `SessionStart` (matcher `startup|resume`), `UserPromptSubmit`
(turn start, eight-second timeout, failures let the prompt through),
`PostToolUse` (matcher `Edit|Write|MultiEdit|apply_patch`) and `Stop`.

- After-edit feedback: agent.
- Stop keeps the agent working: yes.
- Warning channel: yes.
- Seen firing: Claude Code 2.1.326, 2026-11-16.

Session state reached the agent as context, the after-edit findings reached
the agent, and the stop's message kept the agent working once. The same hooks in
the plugin and in a project's settings both fire, which is why a project wired
by an earlier release must be updated (`agent-hooks.md`). Interactive Claude
Code was not tried; whether a trust prompt appears there is unknown.

## Codex CLI

File: the same `hooks/hooks.json`; `--emit auto` renders as Codex when the
environment has `PLUGIN_ROOT`.

- After-edit feedback: agent, for edits made through `apply_patch`; a file
  written through the shell fires nothing.
- Stop keeps the agent working: yes.
- Warning channel: yes.
- Seen firing: Codex 0.167.0, 2026-11-16.

Install the plugin from the marketplace, then approve each hook in `/hooks`.
An unapproved hook is skipped without a word, `codex exec` included, and a
changed script needs approval again. Codex copies the plugin when it installs
it, so a plugin update needs a reinstall. Codex loads no plugin hooks from a
plugin whose root `plugin.json` declares the Agent Plugins schema; the
plugin's manifest declares none. Codex runs hooks in a login shell (`$SHELL
-lc`): startup files that print to stdout can break the hook's JSON.

## Kiro CLI

File: `hooks/kiro/upspec.json` (schema `v1`; hooks for `SessionStart`,
`UserPromptSubmit`, `PostToolUse` with matcher `write`, and `Stop`). Kiro shows
no way for a package to carry hooks, so the person places two things: the
plugin's skill folders in `~/.kiro/skills/`, and this file in `~/.kiro/hooks/`.
Each command calls the gate in
`~/.kiro/skills/up-bootstrapping-spec-driven-projects/scripts/` and does
nothing when it is absent.

- Engine: hooks run only on the V3 engine. With `--no-interactive` and no
  setting Kiro picks V2, which runs none; set `kiro-cli settings
  chat.agentEngine v3` once, or pass `--agent-engine v3`.
- After-edit feedback: person (the agent does not receive it).
- Stop keeps the agent working: yes.
- Warning channel: yes.
- Seen firing: Kiro CLI 3.3.0, 2026-11-16.

Session state reached the agent as plain text and the stop's block kept the
agent working once. Trust the workspace so the hooks run. Kiro never receives
exit 1 from these commands: it means continue at the stop, and the commands map
failures to exit 3.

## OpenCode

Files: `hooks/opencode/package.json` and `index.js`, one module with no
dependency. List the folder in the `plugins` array of `opencode.json`, in the
project or globally. The module finds the gate beside it from its own location
and runs it with `--emit raw`. One OpenCode server serves every session, so the
module drops every event whose location is not its own project.

- After-edit feedback: agent, through the session's instructions entry.
- Stop keeps the agent working: yes (one prompt after the first
  `session.execution.succeeded` that carries a result 2).
- Warning channel: no.
- Seen firing: OpenCode 2.3.0, 2026-11-16.

Session start, turn start and after-edit text go into the session's
instructions entry; no prompt appears when the module loads.

## Antigravity CLI

Not supported. It has no plugin hooks, and with earlier releases its after-edit
and turn-start moments never reached the agent. The commit hook and the team
pipeline still apply to its work. A project that an earlier release wired for it
(`.agents/hooks.json`) has that wiring retired by `--update`.

## Other tools

These contracts were surveyed; none has an upspec profile yet:

- **Gemini CLI:** `.gemini/settings.json`, SessionStart, AfterTool and
  AfterAgent. JSON `additionalContext` supplies context; `decision: deny`
  with a reason can keep the agent working. Timeouts use milliseconds, and
  exit 3 with text can block, so raw results need translation.
- **Copilot CLI:** sessionStart, postToolUse and agentStop. JSON
  `additionalContext` supplies context and `decision: block` can continue
  work; exit 2 with stderr only warns. It can also read Claude settings,
  which does not make their exit meanings identical.
- **Cursor:** sessionStart, afterFileEdit and stop. It reads
  `additional_context`, `followup_message` and `user_message`; stop has a
  loop count and a five-continuation cap. It can import Claude settings,
  but needs its own output contract.

Profiles for Gemini CLI, Copilot CLI and Cursor are planned ideas. These and
other tools without a profile have no upspec hooks. The commit hook and team
pipeline still apply to their work.
