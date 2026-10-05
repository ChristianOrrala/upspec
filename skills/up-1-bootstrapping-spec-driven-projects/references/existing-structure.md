# Existing structure and the A-files

What setup does when the project already has specifications somewhere, or
tracks its work in the A-files. The owner decides; nothing moves before a
yes.

## Specifications found elsewhere

| Found | Full alignment | Keep what is there |
|---|---|---|
| This method's files in another folder (`specs/use_cases/UC-001-....md`, `documentation/specs/...`) | Move them into `docs/` with `scripts/relink.py` | Record the folder: `scaffold_docs.py --specs-folder documentation/specs` writes `**Specs folder:** documentation/specs` into the rules block, which then names that folder in its paths, and every script of the skills reads it |
| Another method's specifications (Spec Kit's `specs/`, Kiro's `.kiro/specs/`, OpenSpec's `openspec/`, loose documents) | Convert them with `up-recovering-specs-from-code`, which reads them as evidence beside the code; each recovered use case cites its source in the ledger; after the baseline review and the owner's yes the old files move to `docs/recovery/sources/` with `scripts/relink.py`, which rewrites the ledger's citations and every link | Keep them as reference documents: the skills neither check nor update them, and new or changed behavior is specified in `docs/` |

Kiro reads only `.kiro/specs/`: removing that folder ends Kiro's own spec
feature in the project. Say so when the owner chooses full alignment.

The specification folder may sit anywhere inside the project; the scripts
find the project's root from the guideline file that records it.

## Moving files with their references

`scripts/relink.py` runs in three steps:

```bash
python3 scripts/relink.py plan   --move specs/use_cases docs/use_cases --root .
python3 scripts/relink.py apply  --move specs/use_cases docs/use_cases --root .
python3 scripts/relink.py verify --move specs/use_cases docs/use_cases --root .
```

`plan` lists every link, image, link definition, `@file` import, backticked
path and settings, CI or hook path that names an old path (`REWRITE`), and
each bare name in prose or reference to a removed file (`DECIDE`). Lines of
agent instruction files carry `[instruction]`: propose for each whether to
remove it, adapt it to the new place or keep it. `apply` moves with `git mv`
and rewrites the `REWRITE` lines. A folder whose new path is an existing
folder moves into it file by file; a file whose new path exists is refused,
so its content is merged and the old file removed first.
`verify` fails while a link is broken or an old path is still named. Links
from outside the repository cannot be checked: say so in the report.

## The A-files

The A-files track a repository's work in five files at the root:
`AGENTS.md`, `ACTIVE.md`, `ABILITIES.md`, `AHEAD.md`, `ATLAS.md`. They are
present when `ACTIVE.md` holds the line `<!-- hot zone ends -->`.

**When they are present**, the scaffold's dry run adds the joining edits, P1
and P5 of the pairing contract in the conventions:

- `AGENTS.md`: the rules section is named in the hot zone's `Below:` line (a
  `Below:` line is added above the marker when there is none), and the
  keep-in-step list gains two rows: a use case that changes Status is
  followed by the ability whose `Specs` line names it; a newly mapped use
  case joins an ability's `Specs` line.
- `ATLAS.md`: one row in the map for the specifications.

A missing Keep in step list or map table is reported as a note; add those
rows by hand. After `--apply`, run `python3 tools/check_tracking.py` until it
prints nothing: the rules block may have taken `AGENTS.md` over its cap.
Running setup again changes nothing.

**When they are not present**, ask once whether the owner wants them. On a
yes:

1. If the `a-files` skill is available, stop before writing anything, adopt
   the A-files with that skill, then run this setup again; it joins them.
2. If it is not, say how to get it (installed from the marketplace that lists
   it, or its skill folder copied into the agent's skills folder), and finish
   the setup without them. A later run of this setup joins them.

Never write the five files from memory: their shape is checked.
